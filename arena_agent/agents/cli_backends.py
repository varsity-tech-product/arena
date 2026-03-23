"""Shared CLI backend utilities for arena agent LLM integrations.

Used by the setup agent (auto mode) to invoke Claude, Gemini, Codex,
and OpenClaw CLIs.  These functions are backend-agnostic helpers for
resolving backends, extracting usage data, and managing sessions.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

VALID_BACKENDS = ("auto", "codex", "claude", "gemini", "openclaw")

_FENCE_RE_PATTERN = None


def _extract_usage(wrapper: dict[str, Any] | None, backend: str) -> dict[str, Any] | None:
    """Normalize token/cost data from CLI wrapper JSON into a standard dict.

    Returns ``{input_tokens, output_tokens, cache_read_input_tokens, cost_usd,
    duration_ms}`` with None values stripped, or None if no usage data is found.
    """
    if not isinstance(wrapper, dict):
        return None

    usage: dict[str, Any] = {}

    if backend == "claude":
        raw = wrapper.get("usage")
        if isinstance(raw, dict):
            usage["input_tokens"] = raw.get("input_tokens")
            usage["output_tokens"] = raw.get("output_tokens")
            usage["cache_read_input_tokens"] = raw.get("cache_read_input_tokens")
        usage["cost_usd"] = wrapper.get("cost_usd")
        usage["duration_ms"] = wrapper.get("duration_ms")
    elif backend == "gemini":
        raw = wrapper.get("stats") or wrapper.get("usage")
        if isinstance(raw, dict):
            usage["input_tokens"] = raw.get("input_tokens")
            usage["output_tokens"] = raw.get("output_tokens")
        usage["cost_usd"] = wrapper.get("cost_usd")
        usage["duration_ms"] = wrapper.get("duration_ms")
    elif backend == "openclaw":
        meta = wrapper.get("meta")
        if isinstance(meta, dict):
            usage["duration_ms"] = meta.get("durationMs")
            agent_meta = meta.get("agentMeta")
            if isinstance(agent_meta, dict):
                raw_usage = agent_meta.get("usage") or {}
                usage["input_tokens"] = raw_usage.get("input")
                usage["output_tokens"] = raw_usage.get("output")
                usage["cache_read_input_tokens"] = raw_usage.get("cacheRead")
                usage["model"] = agent_meta.get("model")
                usage["provider"] = agent_meta.get("provider")
                usage["session_id"] = agent_meta.get("sessionId")

    # Strip None values
    usage = {k: v for k, v in usage.items() if v is not None}
    return usage if usage else None


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) from LLM output."""
    global _FENCE_RE_PATTERN
    if _FENCE_RE_PATTERN is None:
        _FENCE_RE_PATTERN = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?\s*```$", re.DOTALL)
    match = _FENCE_RE_PATTERN.match(text.strip())
    return match.group(1).strip() if match else text.strip()


def _clear_openclaw_sessions(agent_id: str) -> None:
    """Remove session transcript files for an openclaw agent.

    OpenClaw appends every ``--agent`` call to a persistent session.  Over
    many ticks the transcript grows to hundreds-of-thousands of tokens,
    fills the model's context window, and causes truncated responses.

    Clearing the ``.jsonl`` transcripts before each call keeps every
    invocation stateless while preserving the agent's config, model, and
    auth settings.
    """
    sessions_dir = Path.home() / ".openclaw" / "agents" / agent_id / "sessions"
    if not sessions_dir.is_dir():
        return
    for transcript in sessions_dir.glob("*.jsonl"):
        try:
            transcript.unlink()
        except OSError:
            pass


def _find_fallback_backend(current: str) -> str | None:
    """Find an alternative CLI backend available in PATH."""
    preference = ["claude", "gemini", "codex", "openclaw"]
    for candidate in preference:
        if candidate != current and shutil.which(candidate):
            return candidate
    return None


def resolve_backend(backend: str, command: str | None) -> str:
    """Determine which CLI backend to use.

    Returns ``"claude"``, ``"gemini"``, ``"openclaw"``, or ``"codex"``.
    """
    if backend in ("codex", "claude", "gemini", "openclaw"):
        return backend
    if backend != "auto":
        raise ValueError(f"Invalid backend {backend!r}. Must be one of {VALID_BACKENDS}.")
    if command is not None:
        cmd_name = Path(command).name
        if "claude" in cmd_name:
            return "claude"
        if "gemini" in cmd_name:
            return "gemini"
        if "openclaw" in cmd_name:
            return "openclaw"
        return "codex"
    # Auto-detect from PATH.
    if shutil.which("claude"):
        return "claude"
    if shutil.which("gemini"):
        return "gemini"
    if shutil.which("openclaw"):
        return "openclaw"
    if shutil.which("codex"):
        return "codex"
    raise RuntimeError(
        "No supported CLI found in PATH (claude, gemini, openclaw, codex). "
        "Install one or set backend explicitly in the policy config."
    )
