"""
Bot Framework — shared base class, indicators, run loop, risk management.
"""

import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd

from varsity_tools import (
    get_klines,
    get_live_account,
    get_live_position,
    get_live_trades,
    get_market_info,
    trade_close,
    trade_open,
)

# ── Constants ────────────────────────────────────────────────────────────────

COMPETITION_ID = 4
SYMBOL = "BTCUSDT"
INTERVAL = "1m"
POLL_INTERVAL = 30        # seconds between loop iterations
RUN_DURATION = 3600        # 1 hour per strategy
MAX_TRADES_PER_STRATEGY = 12
POSITION_SIZE_PCT = 0.10   # 10% of balance per trade
SL_PCT = 0.015             # 1.5% stop loss
TP_PCT = 0.03              # 3% take profit
MIN_QTY = 0.001
QTY_PRECISION = 3
PRICE_PRECISION = 2

# ── Indicator Functions ──────────────────────────────────────────────────────


def compute_sma(closes: pd.Series, period: int) -> pd.Series:
    """Simple moving average."""
    return closes.rolling(window=period).mean()


def compute_rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    """RSI using Wilder's smoothing (ewm with com=period-1)."""
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_highest(highs: pd.Series, period: int) -> pd.Series:
    """Rolling maximum."""
    return highs.rolling(window=period).max()


def compute_lowest(lows: pd.Series, period: int) -> pd.Series:
    """Rolling minimum."""
    return lows.rolling(window=period).min()


# ── Performance Tracker ──────────────────────────────────────────────────────


@dataclass
class PerformanceTracker:
    strategy_name: str
    trades_opened: int = 0
    trades_closed: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    start_balance: float = 0.0
    end_balance: float = 0.0

    def record_trade(self, pnl: float):
        self.trades_closed += 1
        self.total_pnl += pnl
        if pnl >= 0:
            self.wins += 1
        else:
            self.losses += 1

    def summary(self) -> str:
        win_rate = (self.wins / self.trades_closed * 100) if self.trades_closed > 0 else 0.0
        return (
            f"\n{'='*50}\n"
            f"  Strategy: {self.strategy_name}\n"
            f"  Trades opened: {self.trades_opened}\n"
            f"  Trades closed: {self.trades_closed}\n"
            f"  Wins: {self.wins} | Losses: {self.losses} | Win Rate: {win_rate:.1f}%\n"
            f"  Total PnL: ${self.total_pnl:.2f}\n"
            f"  Start balance: ${self.start_balance:.2f}\n"
            f"  End balance: ${self.end_balance:.2f}\n"
            f"{'='*50}\n"
        )


# ── Helper Functions ─────────────────────────────────────────────────────────


def calculate_size(balance: float, price: float) -> float:
    """Compute BTC quantity: 10% of balance / price, rounded down to 3 decimals."""
    raw = balance * POSITION_SIZE_PCT / price
    qty = math.floor(raw * 10**QTY_PRECISION) / 10**QTY_PRECISION
    return max(qty, MIN_QTY)


def calculate_tp_sl(price: float, direction: str) -> tuple[float, float]:
    """Return (take_profit, stop_loss) rounded to 2 decimals."""
    if direction == "long":
        tp = round(price * (1 + TP_PCT), PRICE_PRECISION)
        sl = round(price * (1 - SL_PCT), PRICE_PRECISION)
    else:
        tp = round(price * (1 - TP_PCT), PRICE_PRECISION)
        sl = round(price * (1 + SL_PCT), PRICE_PRECISION)
    return tp, sl


def fetch_klines_safe(symbol: str = SYMBOL, interval: str = INTERVAL, size: int = 100) -> pd.DataFrame | None:
    """Fetch klines and return as DataFrame, or None on error."""
    try:
        data = get_klines(symbol, interval, size)
        if not data:
            return None
        # API returns {"symbol":..., "interval":..., "klines": [...]}
        candles = data.get("klines", data) if isinstance(data, dict) else data
        if not candles:
            return None
        df = pd.DataFrame(candles)
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception as e:
        _log(f"[ERROR] fetch_klines failed: {e}")
        return None


def _extract_pnl(result) -> float:
    """Extract PnL from a trade close response, trying multiple field names."""
    if not isinstance(result, dict):
        return 0.0
    for key in ("pnl", "realizedPnl", "realized_pnl"):
        val = result.get(key)
        if val is not None:
            return float(val)
    return 0.0


def _log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ── Base Strategy ────────────────────────────────────────────────────────────


class BaseStrategy(ABC):
    def __init__(self, name: str, max_trades: int = MAX_TRADES_PER_STRATEGY):
        self.name = name
        self.max_trades = max_trades
        self.tracker = PerformanceTracker(strategy_name=name)
        self.trades_used = 0
        self.last_open_time = 0.0  # cooldown tracking

    @abstractmethod
    def evaluate(self, klines: pd.DataFrame, current_price: float, position: dict | None) -> str | None:
        """Return 'long', 'short', 'close', or None."""
        ...

    def run(self):
        _log(f"{'='*50}")
        _log(f"Starting strategy: {self.name}")
        _log(f"{'='*50}")

        # Record starting balance
        try:
            acct = get_live_account(COMPETITION_ID)
            self.tracker.start_balance = float(acct.get("availableBalance", acct.get("capital", 0)))
        except Exception as e:
            _log(f"[ERROR] Could not get starting balance: {e}")

        start_time = time.time()
        iteration = 0

        while time.time() - start_time < RUN_DURATION:
            iteration += 1
            _log(f"--- {self.name} | Iteration {iteration} ---")

            try:
                self._iteration()
            except Exception as e:
                _log(f"[ERROR] Iteration failed: {e}")

            elapsed = time.time() - start_time
            remaining = RUN_DURATION - elapsed
            if remaining > POLL_INTERVAL:
                time.sleep(POLL_INTERVAL)
            else:
                break

        # End of hour: force-close any open position
        self._force_close()

        # Record ending balance
        try:
            acct = get_live_account(COMPETITION_ID)
            self.tracker.end_balance = float(acct.get("availableBalance", acct.get("capital", 0)))
        except Exception as e:
            _log(f"[ERROR] Could not get ending balance: {e}")

        _log(f"Strategy {self.name} finished.")
        _log(self.tracker.summary())

    def _iteration(self):
        # 1. Check global trade count
        try:
            trades = get_live_trades(COMPETITION_ID)
            global_trades_used = len(trades) if isinstance(trades, list) else 0
        except Exception as e:
            _log(f"[WARN] Could not fetch trades: {e}")
            global_trades_used = 0

        if global_trades_used >= 40:
            _log("Global trade limit reached (40). Skipping.")
            return

        # 2. Get balance
        try:
            acct = get_live_account(COMPETITION_ID)
            balance = float(acct.get("availableBalance", acct.get("capital", 0)))
        except Exception as e:
            _log(f"[WARN] Could not fetch account: {e}")
            balance = 5000.0

        # 3. Get current position
        try:
            position = get_live_position(COMPETITION_ID)
        except Exception as e:
            _log(f"[WARN] Could not fetch position: {e}")
            position = None

        # 4. Fetch klines
        klines = fetch_klines_safe()
        if klines is None or len(klines) < 50:
            _log("Not enough kline data. Skipping.")
            return

        # 5. Get current price
        try:
            market = get_market_info(SYMBOL)
            current_price = float(market["lastPrice"])
        except Exception as e:
            _log(f"[WARN] Could not get market price: {e}")
            current_price = float(klines["close"].iloc[-1])

        _log(f"Price: ${current_price:.2f} | Balance: ${balance:.2f} | "
             f"Strategy trades: {self.trades_used}/{self.max_trades} | "
             f"Global trades: {global_trades_used}/40 | "
             f"Position: {position.get('direction', 'none') if position else 'none'}")

        # 6. Evaluate signal
        signal = self.evaluate(klines, current_price, position)

        if signal is None:
            _log("No signal.")
            return

        _log(f"Signal: {signal}")

        # 7. Execute signal
        if signal in ("long", "short"):
            if position:
                _log("Already in a position. Skipping open signal.")
                return
            if self.trades_used >= self.max_trades:
                _log(f"Trade budget exhausted ({self.max_trades}). Skipping.")
                return
            # Cooldown check: 60s between opens
            if time.time() - self.last_open_time < 60:
                _log("Cooldown active (60s between opens). Skipping.")
                return

            size = calculate_size(balance, current_price)
            tp, sl = calculate_tp_sl(current_price, signal)
            _log(f"Opening {signal}: size={size} BTC, TP={tp}, SL={sl}")

            try:
                result = trade_open(COMPETITION_ID, signal, size, take_profit=tp, stop_loss=sl)
                _log(f"Trade opened: {result}")
                self.trades_used += 1
                self.tracker.trades_opened += 1
                self.last_open_time = time.time()
            except Exception as e:
                _log(f"[ERROR] trade_open failed: {e}")

        elif signal == "close":
            if not position:
                _log("No position to close.")
                return

            _log("Closing position.")
            try:
                result = trade_close(COMPETITION_ID)
                _log(f"Trade closed: {result}")
                # Try to extract PnL
                pnl = _extract_pnl(result)
                self.tracker.record_trade(pnl)
            except Exception as e:
                _log(f"[ERROR] trade_close failed: {e}")

    def _force_close(self):
        """Close any open position at end of strategy run."""
        try:
            position = get_live_position(COMPETITION_ID)
            if position:
                _log(f"Force-closing position at end of {self.name}")
                result = trade_close(COMPETITION_ID)
                _log(f"Force close result: {result}")
                pnl = _extract_pnl(result)
                self.tracker.record_trade(pnl)
        except Exception as e:
            _log(f"[ERROR] Force close failed: {e}")
