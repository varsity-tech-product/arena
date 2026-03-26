"""Auto loop status panel — shows setup agent decisions, watchdog, and loop state."""

from __future__ import annotations

import time

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.widgets import Static


_PHASE_STYLES = {
    "runtime": ("bold green", "RUNTIME"),
    "setup": ("bold cyan", "SETUP"),
    "waiting": ("dim", "WAITING"),
    "pre_check": ("dim", "PRE-CHECK"),
    "registering": ("dim", "REGISTERING"),
    "account_check": ("dim", "ACCT CHECK"),
    "error_backoff": ("bold red", "ERROR BACKOFF"),
    "stopped": ("dim", "STOPPED"),
}


def _format_elapsed(started_at: float | None) -> str:
    if started_at is None:
        return "-"
    elapsed = max(0, time.time() - started_at)
    if elapsed < 60:
        return f"{elapsed:.0f}s"
    if elapsed < 3600:
        return f"{elapsed / 60:.1f}m"
    return f"{elapsed / 3600:.1f}h"


class SetupPanel(Static):
    """Displays structured auto loop state from the observability stream."""

    def refresh_view(self, controller) -> None:
        auto = controller.auto_loop_state()

        if not auto.get("active"):
            table = Table(expand=True)
            table.add_column("Info")
            table.add_row("Auto loop not active (start with: arena-agent auto)")
            self.update(Panel(table, title="Auto Loop", border_style="dim"))
            return

        table = Table(expand=True)
        table.add_column("Key", style="dim", width=20)
        table.add_column("Value")

        # Phase with color coding
        phase = auto.get("phase") or "unknown"
        style, label = _PHASE_STYLES.get(phase, ("", phase.upper()))
        elapsed = _format_elapsed(auto.get("phase_started_at"))
        table.add_row("Phase", Text(f"{label}  ({elapsed})", style=style))

        # Cycle
        table.add_row("Cycle", str(auto.get("cycle", 0)))

        # Setup backend
        backend = auto.get("setup_backend") or "-"
        table.add_row("Setup Backend", backend)

        # Last setup decision
        decision = auto.get("last_setup_decision")
        if decision and isinstance(decision, dict):
            action = decision.get("action", "-")
            reason = decision.get("reason", "")
            action_style = "green" if action == "update" else ""
            table.add_row("Last Decision", Text(action, style=action_style))
            if reason:
                table.add_row("Reason", reason[:80])
            overrides = decision.get("overrides_summary", "")
            if overrides:
                table.add_row("Overrides", overrides[:80])
        else:
            table.add_row("Last Decision", "-")

        # Next setup check
        next_check = auto.get("next_setup_check_seconds")
        if next_check is not None and auto.get("phase") == "runtime":
            phase_started = auto.get("phase_started_at") or time.time()
            remaining = max(0, next_check - (time.time() - phase_started))
            table.add_row("Next Setup In", f"~{remaining:.0f}s")
        elif next_check is not None:
            table.add_row("Setup Interval", f"{next_check:.0f}s")

        # Watchdog
        inactive = auto.get("inactive_cycles", 0)
        inactive_style = "yellow" if inactive > 0 else ""
        inactive_min = auto.get("inactive_minutes", 0)
        watchdog_text = f"{inactive} cycles"
        if inactive_min > 0:
            watchdog_text += f" ({inactive_min}m)"
        table.add_row("Inactive Cycles", Text(watchdog_text, style=inactive_style))

        # Total runtime iterations
        table.add_row("Total Iterations", str(auto.get("total_runtime_iterations", 0)))

        # Setup failures
        failures = auto.get("consecutive_setup_failures", 0)
        fail_style = "red" if failures > 0 else ""
        table.add_row("Setup Failures", Text(str(failures), style=fail_style))

        # Last runtime result
        stop_reason = auto.get("last_runtime_stop_reason")
        if stop_reason:
            rt_iters = auto.get("last_runtime_iterations", "?")
            rt_exec = auto.get("last_runtime_executed", "?")
            table.add_row("Last Runtime", f"{stop_reason} | iters={rt_iters} executed={rt_exec}")

        # Competition
        comp_status = auto.get("competition_status")
        if comp_status:
            table.add_row("Competition", comp_status)

        border = "green" if phase == "runtime" else "cyan" if phase == "setup" else "yellow"
        self.update(Panel(table, title="Auto Loop", border_style=border))
