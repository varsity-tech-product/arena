"""Optional agent-side reward models derived from transition events."""

from __future__ import annotations

from dataclasses import dataclass

from arena_agent.core.models import TransitionEvent


@dataclass(frozen=True, slots=True)
class RewardWeights:
    realized_pnl_weight: float = 1.0
    equity_delta_weight: float = 0.2
    risk_penalty_weight: float = 0.1
    drawdown_penalty_weight: float = 0.05
    trade_cost_weight: float = 1.0
    invalid_action_penalty: float = 1.0
    hold_penalty: float = 0.0


class TransitionRewardModel:
    """Example reward model for agents that want a scalar objective."""

    def __init__(self, weights: RewardWeights | None = None) -> None:
        self.weights = weights or RewardWeights()
        self._peak_equity: float | None = None

    def score(self, transition: TransitionEvent) -> float:
        prior_peak = self._peak_equity
        if prior_peak is None:
            prior_peak = transition.state_before.account.equity

        exposure = 0.0
        if transition.state_after.position is not None:
            exposure = abs(transition.state_after.position.size)
        risk_penalty = exposure * transition.state_after.market.volatility
        drawdown = max(0.0, prior_peak - transition.state_after.account.equity)

        reward = (
            transition.metrics.realized_pnl_delta * self.weights.realized_pnl_weight
            + transition.metrics.equity_delta * self.weights.equity_delta_weight
            - transition.metrics.fee * self.weights.trade_cost_weight
            - risk_penalty * self.weights.risk_penalty_weight
            - drawdown * self.weights.drawdown_penalty_weight
        )

        if not transition.execution_result.accepted and not transition.action.is_hold:
            reward -= self.weights.invalid_action_penalty
        if transition.action.is_hold:
            reward -= self.weights.hold_penalty

        self._peak_equity = max(prior_peak, transition.state_after.account.equity)
        return reward
