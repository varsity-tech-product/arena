from __future__ import annotations

import unittest
from unittest.mock import patch

from arena_agent.__main__ import _apply_agent_override
from arena_agent.core.models import RuntimeConfig


class RunCLITest(unittest.TestCase):
    def test_apply_agent_override_sets_codex_policy(self) -> None:
        config = RuntimeConfig.from_mapping(
            {
                "competition_id": 4,
                "symbol": "BTCUSDT",
                "policy": {"type": "ensemble"},
            }
        )
        args = type(
            "Args",
            (),
            {
                "agent": "codex",
                "codex_model": "gpt-5",
                "codex_timeout_seconds": 60.0,
                "codex_recent_transitions": 5,
                "codex_extra_instructions": "Stay conservative.",
                "strategy_context": "momentum",
            },
        )()

        updated = _apply_agent_override(config, args)

        self.assertEqual(updated.policy["type"], "codex_exec")
        self.assertEqual(updated.policy["model"], "gpt-5")
        self.assertEqual(updated.policy["timeout_seconds"], 24.0)
        self.assertEqual(updated.policy["recent_transition_limit"], 5)
        self.assertEqual(updated.policy["strategy_context"], "momentum")
        self.assertIn("cwd", updated.policy)

    def test_run_subcommand_invokes_runtime(self) -> None:
        config = RuntimeConfig.from_mapping({"competition_id": 4, "symbol": "BTCUSDT"})
        runtime_instance = type(
            "RuntimeStub",
            (),
            {
                "run": lambda self: type(
                    "Report",
                    (),
                    {
                        "iterations": 1,
                        "executed_actions": 0,
                        "transitions_recorded": 0,
                        "total_realized_pnl": 0.0,
                        "total_fees": 0.0,
                        "final_equity": 1000.0,
                    },
                )()
            },
        )()

        with patch("arena_agent.__main__.load_runtime_config", return_value=config), patch(
            "arena_agent.__main__.load_local_runtime_env"
        ), patch("arena_agent.__main__.require_runtime_environment"), patch(
            "arena_agent.__main__.MarketRuntime",
            return_value=runtime_instance,
        ) as runtime_cls:
            from arena_agent.__main__ import main

            main(["run", "--agent", "codex", "--config", "arena_agent/config/agent_config.yaml"])

        self.assertEqual(runtime_cls.call_args.args[0].policy["type"], "codex_exec")


if __name__ == "__main__":
    unittest.main()
