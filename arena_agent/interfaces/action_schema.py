"""Action schema shared across policies and execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ActionType(str, Enum):
    OPEN_LONG = "OPEN_LONG"
    OPEN_SHORT = "OPEN_SHORT"
    CLOSE_POSITION = "CLOSE_POSITION"
    UPDATE_TPSL = "UPDATE_TPSL"
    HOLD = "HOLD"


@dataclass(frozen=True, slots=True)
class Action:
    type: ActionType = ActionType.HOLD
    size: float | None = None
    take_profit: float | None = None
    stop_loss: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_hold(self) -> bool:
        return self.type == ActionType.HOLD

    @property
    def is_open(self) -> bool:
        return self.type in {ActionType.OPEN_LONG, ActionType.OPEN_SHORT}

    @property
    def direction(self) -> str | None:
        if self.type == ActionType.OPEN_LONG:
            return "long"
        if self.type == ActionType.OPEN_SHORT:
            return "short"
        return None

    @classmethod
    def hold(cls, reason: str | None = None, **metadata: Any) -> "Action":
        if reason is not None:
            metadata = {**metadata, "reason": reason}
        return cls(type=ActionType.HOLD, metadata=metadata)
