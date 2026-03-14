"""Simple indicator helpers implemented without third-party dependencies."""

from __future__ import annotations

from typing import Sequence


def sma(values: Sequence[float], period: int) -> float | None:
    if len(values) < period:
        return None
    window = values[-period:]
    return sum(window) / period


def rolling_sma(values: Sequence[float], period: int) -> list[float | None]:
    result: list[float | None] = []
    for index in range(len(values)):
        if index + 1 < period:
            result.append(None)
        else:
            window = values[index + 1 - period : index + 1]
            result.append(sum(window) / period)
    return result


def rsi(values: Sequence[float], period: int = 14) -> list[float | None]:
    if len(values) < period + 1:
        return [None] * len(values)

    gains = [0.0]
    losses = [0.0]
    for previous, current in zip(values, values[1:]):
        change = current - previous
        gains.append(max(change, 0.0))
        losses.append(abs(min(change, 0.0)))

    average_gain = sum(gains[1 : period + 1]) / period
    average_loss = sum(losses[1 : period + 1]) / period
    readings: list[float | None] = [None] * len(values)

    if average_loss == 0:
        readings[period] = 100.0
    else:
        rs = average_gain / average_loss
        readings[period] = 100 - (100 / (1 + rs))

    for index in range(period + 1, len(values)):
        average_gain = ((average_gain * (period - 1)) + gains[index]) / period
        average_loss = ((average_loss * (period - 1)) + losses[index]) / period
        if average_loss == 0:
            readings[index] = 100.0
        else:
            rs = average_gain / average_loss
            readings[index] = 100 - (100 / (1 + rs))

    return readings
