from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT_DIR = Path(__file__).resolve().parents[1]


class ShellScriptsTest(unittest.TestCase):
    def test_cli_wrappers_work_outside_repo_root(self) -> None:
        scripts = [
            ROOT_DIR / "arena_market_state",
            ROOT_DIR / "arena_trade",
            ROOT_DIR / "arena_last_transition",
            ROOT_DIR / "arena_competition_info",
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            for script in scripts:
                with self.subTest(script=script.name):
                    result = subprocess.run(
                        [str(script), "--help"],
                        cwd=temp_dir,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
                    self.assertIn("usage:", result.stdout.lower())

    def test_run_mcp_server_help_works_outside_repo_root(self) -> None:
        python_bin = ROOT_DIR / ".venv" / "bin" / "python"
        if not python_bin.exists():
            self.skipTest("repo venv is not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [str(ROOT_DIR / "run_mcp_server.sh"), "--help"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        self.assertIn("usage:", result.stdout.lower())
