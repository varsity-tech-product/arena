from __future__ import annotations

import unittest

from arena_agent.__main__ import _deep_merge


class AutoMergeTest(unittest.TestCase):
    def test_strategy_component_type_switch_replaces_stale_params(self) -> None:
        config = {
            "strategy": {
                "sizing": {
                    "type": "volatility_scaled",
                    "target_risk_pct": 0.02,
                    "atr_multiplier": 2.0,
                },
                "tpsl": {
                    "type": "atr_multiple",
                    "atr_tp_mult": 2.0,
                    "atr_sl_mult": 1.5,
                    "min_sl_pct": 0.005,
                },
                "entry_filters": [{"type": "trade_budget", "min_remaining_trades": 5}],
            }
        }
        overrides = {
            "strategy": {
                "sizing": {"type": "fixed_fraction", "fraction": 0.8},
                "tpsl": {"type": "fixed_pct", "tp_pct": 0.018, "sl_pct": 0.007},
            }
        }

        _deep_merge(config, overrides)

        self.assertEqual(config["strategy"]["sizing"], {"type": "fixed_fraction", "fraction": 0.8})
        self.assertEqual(config["strategy"]["tpsl"], {"type": "fixed_pct", "tp_pct": 0.018, "sl_pct": 0.007})
        self.assertEqual(config["strategy"]["entry_filters"], [{"type": "trade_budget", "min_remaining_trades": 5}])

    def test_unrelated_nested_dicts_still_merge_recursively(self) -> None:
        config = {"risk_limits": {"allow_long": True, "allow_short": True}}
        overrides = {"risk_limits": {"max_absolute_size": None}}

        _deep_merge(config, overrides)

        self.assertEqual(
            config["risk_limits"],
            {"allow_long": True, "allow_short": True, "max_absolute_size": None},
        )


if __name__ == "__main__":
    unittest.main()
