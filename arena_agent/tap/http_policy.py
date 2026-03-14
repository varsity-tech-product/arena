"""HTTP-backed TAP policy for external agents."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import requests

from arena_agent.core.models import AgentState, TransitionEvent
from arena_agent.interfaces.action_schema import Action
from arena_agent.interfaces.policy_interface import Policy
from arena_agent.tap.protocol import build_decision_request, parse_decision_response


@dataclass
class HttpTapPolicy(Policy):
    endpoint: str
    timeout_seconds: float = 10.0
    headers: dict[str, str] = field(default_factory=dict)
    fail_open_to_hold: bool = True
    name: str = "tap_http"
    session: Any | None = None

    def __post_init__(self) -> None:
        self._session = self.session or requests.Session()
        self._logger = logging.getLogger("arena_agent.tap")

    def decide(self, state: AgentState) -> Action:
        payload = build_decision_request(state)
        try:
            response = self._session.post(
                self.endpoint,
                json=payload,
                headers=self.headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            return parse_decision_response(response.json())
        except Exception as exc:
            if self.fail_open_to_hold:
                self._logger.warning("TAP decision failed for %s: %s", self.endpoint, exc)
                return Action.hold(reason=f"tap_error:{type(exc).__name__}")
            raise

    def update(self, memory: list[TransitionEvent]) -> None:
        return None
