"""
Strategy 1: MA20/MA50 Crossover (Trend Following)
"""

import pandas as pd

from bot_framework import BaseStrategy, compute_sma, _log


class MACrossoverStrategy(BaseStrategy):
    fast_period = 20
    slow_period = 50

    def __init__(self):
        super().__init__("MA_Crossover")

    def evaluate(self, klines: pd.DataFrame, current_price: float, position: dict | None) -> str | None:
        closes = klines["close"]

        if len(closes) < self.slow_period + 2:
            return None

        ma_fast = compute_sma(closes, self.fast_period)
        ma_slow = compute_sma(closes, self.slow_period)

        # Check crossover using the last two completed candles
        # Use -3 and -2 to avoid the current (incomplete) candle at -1
        prev_fast = ma_fast.iloc[-3]
        prev_slow = ma_slow.iloc[-3]
        curr_fast = ma_fast.iloc[-2]
        curr_slow = ma_slow.iloc[-2]

        if pd.isna(prev_fast) or pd.isna(prev_slow) or pd.isna(curr_fast) or pd.isna(curr_slow):
            return None

        _log(f"  MA20={curr_fast:.2f} MA50={curr_slow:.2f} (prev MA20={prev_fast:.2f} MA50={prev_slow:.2f})")

        # Bullish crossover: MA20 crosses above MA50
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            _log("  Bullish MA crossover detected!")
            if position and position.get("direction") == "short":
                return "close"
            if not position:
                return "long"

        # Bearish crossover: MA20 crosses below MA50
        if prev_fast >= prev_slow and curr_fast < curr_slow:
            _log("  Bearish MA crossover detected!")
            if position and position.get("direction") == "long":
                return "close"
            if not position:
                return "short"

        return None


if __name__ == "__main__":
    strategy = MACrossoverStrategy()
    strategy.run()
