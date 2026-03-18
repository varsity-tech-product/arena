"""Setup agent activity panel — shows auto daemon logs and MCP tool calls."""

from __future__ import annotations

import json
import os
from pathlib import Path

from rich.panel import Panel
from rich.table import Table
from textual.widgets import Static


class SetupPanel(Static):
    """Reads the auto daemon log file and displays recent setup agent activity."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._log_path: str | None = None
        self._last_size: int = 0
        self._lines: list[str] = []

    def set_log_path(self, path: str) -> None:
        self._log_path = path

    def refresh_view(self, controller) -> None:
        # Auto-detect log path from arena home
        if self._log_path is None:
            self._log_path = _find_auto_log(controller)

        lines = self._read_recent_lines(30)

        table = Table(expand=True)
        table.add_column("Time", style="dim", width=8)
        table.add_column("Event")
        if lines:
            for line in lines[-15:]:
                time_str, event = _parse_line(line)
                table.add_row(time_str, event)
        else:
            table.add_row("-", "No setup agent activity (start with: arena-agent auto)")

        title = "Setup Agent Activity"
        if self._log_path:
            title += f" | {os.path.basename(self._log_path)}"
        self.update(Panel(table, title=title, border_style="green"))

    def _read_recent_lines(self, n: int) -> list[str]:
        if not self._log_path or not os.path.exists(self._log_path):
            return []
        try:
            with open(self._log_path, "r") as f:
                f.seek(0, 2)
                size = f.tell()
                # Only re-read if file grew
                if size == self._last_size and self._lines:
                    return self._lines
                self._last_size = size
                # Read last ~4KB
                start = max(0, size - 4096)
                f.seek(start)
                if start > 0:
                    f.readline()  # skip partial line
                self._lines = f.readlines()[-n:]
                return self._lines
        except Exception:
            return []


def _find_auto_log(controller) -> str | None:
    """Try to find the auto daemon log from runtime state."""
    snapshot = controller.snapshot
    runtime = snapshot.get("runtime", {})
    # Check if there's a log path hint from runtime config
    # Fallback: scan logs dir for auto-*.log
    connection = snapshot.get("connection", {})
    host = connection.get("host", "127.0.0.1")
    port = connection.get("port", 8767)
    # Try common arena home locations
    for home in [
        os.path.expanduser("~/.arena-agent"),
        os.path.expanduser("~/.arena-trader-6cff"),
    ]:
        logs_dir = os.path.join(home, "logs")
        if os.path.isdir(logs_dir):
            candidates = sorted(
                Path(logs_dir).glob("auto-daemon*.log"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if candidates:
                return str(candidates[0])
    return None


def _parse_line(line: str) -> tuple[str, str]:
    """Extract time and event from a log line."""
    line = line.strip()
    if not line:
        return ("-", "")
    # Lines from daemon: "Arena auto-trade daemon starting."
    # Lines from Python bridge: "[03/18/26 14:56:08] INFO ..."
    # Lines from our daemon log: "Trading competition #9..."
    parts = line.split(None, 1)
    if len(parts) >= 2 and ":" in parts[0]:
        return parts[0][-8:], parts[1][:80]
    return ("", line[:80])
