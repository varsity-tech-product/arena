"""Helpers for loading the local Arena runtime environment."""

from __future__ import annotations

import os
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
ROOT_DIR = PACKAGE_DIR.parent
CONFIG_DIR = PACKAGE_DIR / "config"


def runtime_root_dir() -> Path:
    env_root = os.environ.get("ARENA_ROOT") or os.environ.get("ARENA_HOME")
    if env_root:
        return Path(env_root).expanduser().resolve()

    cwd = Path.cwd()
    if any(
        (
            (cwd / ".arena-home.json").exists(),
            (cwd / ".env.runtime.local").exists(),
            (cwd / "config").exists(),
            (cwd / "arena_agent" / "__init__.py").exists(),
        )
    ):
        return cwd

    return ROOT_DIR


def default_env_file_path() -> Path:
    return runtime_root_dir() / ".env.runtime.local"


def default_runtime_config_path(filename: str) -> Path:
    runtime_root = runtime_root_dir()
    candidates = [
        runtime_root / "config" / filename,
        runtime_root / "arena_agent" / "config" / filename,
        CONFIG_DIR / filename,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def load_local_runtime_env(env_file: str | None = None, *, override: bool = False) -> Path | None:
    path = Path(env_file).expanduser() if env_file else default_env_file_path()
    if not path.exists():
        return None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if override:
            os.environ[key] = value
        else:
            os.environ.setdefault(key, value)
    return path


def require_runtime_environment() -> None:
    if not os.environ.get("VARSITY_API_KEY", "").strip():
        raise SystemExit("VARSITY_API_KEY must be injected via the runtime environment.")
