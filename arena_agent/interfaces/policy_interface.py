"""Policy abstraction for runtime-compatible agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from arena_agent.core.models import AgentState, TransitionEvent
from arena_agent.interfaces.action_schema import Action


class Policy(ABC):
    name: str

    @abstractmethod
    def decide(self, state: AgentState) -> Action:
        """Map the current state into an action."""

    def update(self, memory: Sequence[TransitionEvent]) -> None:
        """Optional post-step update hook using neutral transition history."""

    def compute_reward(self, transition: TransitionEvent) -> float | None:
        """Optional policy-owned reward calculation."""
        return None

    def reset(self) -> None:
        """Optional lifecycle hook."""
