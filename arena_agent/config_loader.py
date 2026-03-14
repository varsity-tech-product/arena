"""Load runtime configuration from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from arena_agent.core.models import RuntimeConfig


def load_runtime_config(path: str) -> RuntimeConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        payload: dict[str, Any] = yaml.safe_load(handle) or {}
    return RuntimeConfig.from_mapping(payload)
