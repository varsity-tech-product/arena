from __future__ import annotations

import unittest

from arena_agent.__main__ import _apply_agent_override
from arena_agent.core.models import RuntimeConfig


class RunCLITest(unittest.TestCase):
    def test_agent_config_preserves_yaml_policy(self) -> None:
        config = RuntimeConfig.from_mapping(
            {
                "competition_id": 4,
                "symbol": "BTCUSDT",
                "policy": {"type": "ensemble"},
            }
        )
        args = type("Args", (), {"agent": "config"})()
        updated = _apply_agent_override(config, args)
        self.assertEqual(updated.policy["type"], "ensemble")

    def test_agent_rule_preserves_yaml_policy(self) -> None:
        config = RuntimeConfig.from_mapping(
            {
                "competition_id": 4,
                "symbol": "BTCUSDT",
                "policy": {"type": "ma_crossover", "params": {"fast_period": 10}},
            }
        )
        args = type("Args", (), {"agent": "rule"})()
        updated = _apply_agent_override(config, args)
        self.assertEqual(updated.policy["type"], "ma_crossover")

    def test_agent_tap_sets_tap_policy(self) -> None:
        config = RuntimeConfig.from_mapping(
            {
                "competition_id": 4,
                "symbol": "BTCUSDT",
            }
        )
        args = type(
            "Args",
            (),
            {
                "agent": "tap",
                "tap_endpoint": "http://localhost:9090/decision",
                "tap_timeout_seconds": 30.0,
            },
        )()
        updated = _apply_agent_override(config, args)
        self.assertEqual(updated.policy["type"], "tap_http")
        self.assertEqual(updated.policy["endpoint"], "http://localhost:9090/decision")


if __name__ == "__main__":
    unittest.main()
