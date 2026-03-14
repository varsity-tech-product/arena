"""
Orchestrator — runs all 3 strategies sequentially (1 hour each, ~3 hours total).
"""

from datetime import datetime, timezone

from strategy_1_ma import MACrossoverStrategy
from strategy_2_rsi import RSIMeanReversionStrategy
from strategy_3_breakout import BreakoutStrategy


def main():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"\n{'#'*60}")
    print(f"  Auto-Trading Bot — Starting at {ts}")
    print(f"{'#'*60}\n")

    strategies = [
        MACrossoverStrategy(),
        RSIMeanReversionStrategy(),
        BreakoutStrategy(),
    ]

    summaries = []

    for i, strategy in enumerate(strategies, 1):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"\n>>> Strategy {i}/3: {strategy.name} starting at {ts}")
        strategy.run()
        summaries.append(strategy.tracker.summary())

    # Combined summary
    print(f"\n{'#'*60}")
    print("  COMBINED RESULTS")
    print(f"{'#'*60}")
    for s in summaries:
        print(s)

    total_opened = sum(st.tracker.trades_opened for st in strategies)
    total_pnl = sum(st.tracker.total_pnl for st in strategies)
    print(f"  Total trades opened across all strategies: {total_opened}")
    print(f"  Total combined PnL: ${total_pnl:.2f}")
    print(f"{'#'*60}\n")


if __name__ == "__main__":
    main()
