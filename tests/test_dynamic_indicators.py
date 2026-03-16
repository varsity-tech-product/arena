"""Tests for dynamic indicator requests from the agent."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from arena_agent.core.models import Candle, FeatureSpec, RuntimeConfig
from arena_agent.core.state_builder import StateBuilder
from arena_agent.features.engine import FeatureEngine, compute_kline_limit, API_MAX_KLINES
from arena_agent.features.registry import feature_key


def _make_candles(n: int = 120) -> list[Candle]:
    return [
        Candle(i, i + 1, 100 + i * 0.5, 101 + i * 0.5, 99 + i * 0.5, 100 + i * 0.5, 10 + i)
        for i in range(n)
    ]


class StateBuilderAddIndicatorsTest(unittest.TestCase):
    def test_add_new_indicator(self) -> None:
        config = RuntimeConfig.from_mapping({
            "competition_id": 4,
            "symbol": "BTCUSDT",
            "signal_indicators": [
                {"indicator": "SMA", "params": {"period": 20}},
            ],
        })
        adapter = MagicMock()
        builder = StateBuilder(adapter, config)

        self.assertEqual(len(builder.feature_engine.feature_specs), 1)

        added = builder.add_indicators([
            {"indicator": "SMA", "params": {"period": 200}},
            {"indicator": "RSI", "params": {"period": 7}},
        ])

        self.assertEqual(added, 2)
        self.assertEqual(len(builder.feature_engine.feature_specs), 3)

    def test_deduplicates_existing(self) -> None:
        config = RuntimeConfig.from_mapping({
            "competition_id": 4,
            "symbol": "BTCUSDT",
            "signal_indicators": [
                {"indicator": "SMA", "params": {"period": 20}},
            ],
        })
        adapter = MagicMock()
        builder = StateBuilder(adapter, config)

        added = builder.add_indicators([
            {"indicator": "SMA", "params": {"period": 20}},  # duplicate
        ])

        self.assertEqual(added, 0)
        self.assertEqual(len(builder.feature_engine.feature_specs), 1)

    def test_skips_invalid_specs(self) -> None:
        config = RuntimeConfig.from_mapping({
            "competition_id": 4,
            "symbol": "BTCUSDT",
        })
        adapter = MagicMock()
        builder = StateBuilder(adapter, config)

        added = builder.add_indicators([
            "not a dict",
            {"no_indicator_key": True},
            {"indicator": "ATR", "params": {"period": 14}},
        ])

        self.assertEqual(added, 1)

    def test_new_indicators_compute_on_next_call(self) -> None:
        engine = FeatureEngine([
            FeatureSpec(indicator="SMA", params={"period": 20}),
        ])
        candles = _make_candles(120)

        # Before: only SMA(20)
        state1 = engine.compute(candles)
        self.assertIn("sma_20", state1.values)
        self.assertNotIn("sma_100", state1.values)

        # Agent requests SMA(100)
        engine.feature_specs.append(FeatureSpec(indicator="SMA", params={"period": 100}))

        # After: both SMA(20) and SMA(100) computed
        state2 = engine.compute(candles)
        self.assertIn("sma_20", state2.values)
        self.assertIn("sma_100", state2.values)
        self.assertIsNotNone(state2.values["sma_100"])


class ComputeKlineLimitTest(unittest.TestCase):
    def test_small_indicators_use_minimum(self) -> None:
        specs = [
            FeatureSpec(indicator="SMA", params={"period": 20}),
            FeatureSpec(indicator="RSI", params={"period": 14}),
        ]
        # max lookback = 20, + margin 20 = 40, but minimum is 120
        self.assertEqual(compute_kline_limit(specs, minimum=120), 120)

    def test_large_indicator_increases_limit(self) -> None:
        specs = [
            FeatureSpec(indicator="SMA", params={"period": 200}),
        ]
        # lookback 200 + margin 20 = 220, > minimum 120
        self.assertEqual(compute_kline_limit(specs, minimum=120), 220)

    def test_capped_at_api_max(self) -> None:
        specs = [
            FeatureSpec(indicator="SMA", params={"period": 990}),
        ]
        # lookback 990 + margin 20 = 1010, but API max is 1000
        self.assertEqual(compute_kline_limit(specs, minimum=120), API_MAX_KLINES)

    def test_empty_specs_use_minimum(self) -> None:
        self.assertEqual(compute_kline_limit([], minimum=120), 120)

    def test_macd_lookback(self) -> None:
        specs = [
            FeatureSpec(indicator="MACD", params={"fast_period": 12, "slow_period": 26, "signal_period": 9}),
        ]
        # MACD lookback = 26 + 9 = 35, + margin 20 = 55, minimum 120 wins
        self.assertEqual(compute_kline_limit(specs, minimum=120), 120)


class KlineLimitAutoAdjustTest(unittest.TestCase):
    def test_state_builder_auto_calculates_kline_limit(self) -> None:
        config = RuntimeConfig.from_mapping({
            "competition_id": 4,
            "symbol": "BTCUSDT",
            "kline_limit": 120,
            "signal_indicators": [
                {"indicator": "SMA", "params": {"period": 200}},
            ],
        })
        adapter = MagicMock()
        builder = StateBuilder(adapter, config)
        # SMA(200) lookback = 200 + 20 margin = 220 > config's 120
        self.assertEqual(builder._kline_limit, 220)

    def test_dynamic_indicator_recalculates(self) -> None:
        config = RuntimeConfig.from_mapping({
            "competition_id": 4,
            "symbol": "BTCUSDT",
            "kline_limit": 120,
            "signal_indicators": [
                {"indicator": "RSI", "params": {"period": 14}},
            ],
        })
        adapter = MagicMock()
        builder = StateBuilder(adapter, config)
        # Initially: RSI(14) lookback=14, +20=34, minimum=120
        self.assertEqual(builder._kline_limit, 120)

        # Agent requests SMA(500) dynamically
        builder.add_indicators([{"indicator": "SMA", "params": {"period": 500}}])
        # Now: SMA(500) lookback=500, +20=520 > 120
        self.assertEqual(builder._kline_limit, 520)

    def test_dynamic_indicator_capped_at_api_max(self) -> None:
        config = RuntimeConfig.from_mapping({
            "competition_id": 4,
            "symbol": "BTCUSDT",
            "kline_limit": 120,
        })
        adapter = MagicMock()
        builder = StateBuilder(adapter, config)

        builder.add_indicators([{"indicator": "SMA", "params": {"period": 999}}])
        # 999 + 20 = 1019 → capped at 1000
        self.assertEqual(builder._kline_limit, API_MAX_KLINES)


class ProtocolIndicatorsTest(unittest.TestCase):
    def test_indicators_extracted_to_metadata(self) -> None:
        from arena_agent.tap.protocol import parse_decision_response

        payload = {
            "action": {
                "type": "HOLD",
                "size": None,
                "take_profit": None,
                "stop_loss": None,
                "confidence": 0.5,
                "reason": "need more data",
                "indicators": [
                    {"indicator": "SMA", "params": {"period": 200}},
                ],
            }
        }
        action = parse_decision_response(payload)
        self.assertEqual(action.metadata["indicators"], [{"indicator": "SMA", "params": {"period": 200}}])


if __name__ == "__main__":
    unittest.main()
