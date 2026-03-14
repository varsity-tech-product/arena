"""Structured event journal for runtime decisions and executions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TradeJournal:
    def __init__(self, output_path: str | None = None) -> None:
        self.output_path = Path(output_path) if output_path else None

    def record(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.output_path is None:
            return
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"event_type": event_type, **payload}, sort_keys=True))
            handle.write("\n")
