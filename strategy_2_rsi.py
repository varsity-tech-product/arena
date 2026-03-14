"""
Strategy 2: RSI(14) Mean Reversion
"""

import pandas as pd

from bot_framework import BaseStrategy, compute_rsi, _log


class RSIMeanReversionStrategy(BaseStrategy):
    rsi_period = 14
    oversold = 30
    overbought = 70
    exit_level = 50

    def __init__(self):
        super().__init__("RSI_MeanReversion")

    def evaluate(self, klines: pd.DataFrame, current_price: float, position: dict | None) -> str | None:
        closes = klines["close"]

        if len(closes) < self.rsi_period + 3:
            return None

        rsi = compute_rsi(closes, self.rsi_period)

        # Use -3 and -2 to avoid the current (incomplete) candle
        prev_rsi = rsi.iloc[-3]
        curr_rsi = rsi.iloc[-2]

        if pd.isna(prev_rsi) or pd.isna(curr_rsi):
            return None

        _log(f"  RSI={curr_rsi:.2f} (prev={prev_rsi:.2f})")

        # Exit logic: RSI crosses through 50 toward neutral
        if position:
            direction = position.get("direction")
            if direction == "long" and prev_rsi < self.exit_level and curr_rsi >= self.exit_level:
                _log("  RSI crossed above 50 — closing long")
                return "close"
            if direction == "short" and prev_rsi > self.exit_level and curr_rsi <= self.exit_level:
                _log("  RSI crossed below 50 — closing short")
                return "close"

        # Entry: RSI crosses into oversold zone
        if prev_rsi >= self.oversold and curr_rsi < self.oversold:
            _log("  RSI entered oversold — long signal")
            if not position:
                return "long"

        # Entry: RSI crosses into overbought zone
        if prev_rsi <= self.overbought and curr_rsi > self.overbought:
            _log("  RSI entered overbought — short signal")
            if not position:
                return "short"

        return None


if __name__ == "__main__":
    strategy = RSIMeanReversionStrategy()
    strategy.run()
