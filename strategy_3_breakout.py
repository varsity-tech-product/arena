"""
Strategy 3: 20-Period Channel Breakout
"""

import pandas as pd

from bot_framework import BaseStrategy, compute_highest, compute_lowest, _log


class BreakoutStrategy(BaseStrategy):
    lookback = 20

    def __init__(self):
        super().__init__("Channel_Breakout")

    def evaluate(self, klines: pd.DataFrame, current_price: float, position: dict | None) -> str | None:
        if len(klines) < self.lookback + 2:
            return None

        # Compute channel on completed candles (exclude current incomplete candle)
        # Use highs/lows from candle [-lookback-1] to candle [-2] (the last completed)
        highs = klines["high"].iloc[-(self.lookback + 1):-1]
        lows = klines["low"].iloc[-(self.lookback + 1):-1]

        channel_high = highs.max()
        channel_low = lows.min()

        if pd.isna(channel_high) or pd.isna(channel_low):
            return None

        _log(f"  Channel: high={channel_high:.2f} low={channel_low:.2f} price={current_price:.2f}")

        # If in position, check for opposite breakout → close
        if position:
            direction = position.get("direction")
            if direction == "long" and current_price < channel_low:
                _log("  Price broke below channel — closing long")
                return "close"
            if direction == "short" and current_price > channel_high:
                _log("  Price broke above channel — closing short")
                return "close"
            return None

        # No position: check for breakout entries
        if current_price > channel_high:
            _log("  Breakout above channel — long signal")
            return "long"

        if current_price < channel_low:
            _log("  Breakout below channel — short signal")
            return "short"

        return None


if __name__ == "__main__":
    strategy = BreakoutStrategy()
    strategy.run()
