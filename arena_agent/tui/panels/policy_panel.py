"""Policy and runtime config panel."""

from __future__ import annotations

from rich.panel import Panel
from rich.table import Table
from textual.widgets import Static


class PolicyPanel(Static):
    def refresh_view(self, controller) -> None:
        info = controller.policy_info()
        table = Table.grid(padding=(0, 2))
        table.add_column("Label", style="cyan")
        table.add_column("Value")
        table.add_row("Policy", str(info.get("policy_name", "-")))
        table.add_row("Backend", str(info.get("backend", "-")))
        table.add_row("Indicator Mode", str(info.get("indicator_mode", "-")))
        table.add_row("Timeout", f"{info.get('timeout_seconds', '-')}s")
        table.add_row("Tick Interval", f"{info.get('tick_interval_seconds', '-')}s")
        table.add_row("Strategy Context", str(info.get("strategy_context", "-")))
        table.add_row("Sizing", str(info.get("sizing_type", "-")))
        table.add_row("TP/SL", str(info.get("tpsl_type", "-")))
        table.add_row("Competition", str(info.get("competition_id", "-")))
        table.add_row("Dry Run", str(info.get("dry_run", "-")))
        self.update(Panel(table, title="Policy & Config", border_style="cyan"))
