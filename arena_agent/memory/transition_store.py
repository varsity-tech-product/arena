"""Transition buffer with optional JSONL persistence."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Iterable

from arena_agent.core.models import TransitionEvent
from arena_agent.core.serialization import to_jsonable


class TransitionStore:
    def __init__(self, maxlen: int = 1000, output_path: str | None = None) -> None:
        self._items: deque[TransitionEvent] = deque(maxlen=maxlen)
        self.output_path = Path(output_path) if output_path else None

    def append(self, transition: TransitionEvent) -> None:
        self._items.append(transition)
        if self.output_path is not None:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            with self.output_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(to_jsonable(transition), sort_keys=True))
                handle.write("\n")

    def recent(self, limit: int | None = None) -> list[TransitionEvent]:
        items = list(self._items)
        if limit is None or limit >= len(items):
            return items
        return items[-limit:]

    def all(self) -> list[TransitionEvent]:
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterable[TransitionEvent]:
        return iter(self._items)
