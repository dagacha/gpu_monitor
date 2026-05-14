"""
Memory Panel — shows memory rows dynamically from MemoryStats.
Uses shared common.types and widgets.util.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from common.types import MemoryStats
from common.widgets.util import bar, fmt_mb


class MemPanel(Widget):
    DEFAULT_CSS = """
    MemPanel {
        border: solid $accent;
        border-title-color: $accent;
        padding: 0 1;
        height: auto;
    }
    MemPanel #mem-rows {
        height: auto;
    }
    MemPanel #mem-note {
        color: $text-muted;
        margin-top: 1;
    }
    """

    mem_stats: reactive[MemoryStats | None] = reactive(None)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "Memory"

    def compose(self) -> ComposeResult:
        # Dynamic rows will be mounted in _update
        yield Static(id="mem-rows")

    def on_mount(self) -> None:
        self._update()

    def watch_mem_stats(self, _: MemoryStats | None) -> None:
        self._update()

    def _update(self) -> None:
        mem = self.mem_stats
        container = self.query_one("#mem-rows", Static)

        if mem is None or not mem.available or not mem.rows:
            container.update("[dim]No memory data available[/]")
            return

        lines = []
        for row in mem.rows:
            if row.total_mb is not None:
                lines.append(
                    f"[bold]{row.label}[/]  "
                    f"Total: {fmt_mb(row.total_mb)}  "
                    f"Used: {row.pct:.1f}%  "
                    f"{fmt_mb(row.used_mb)}"
                )
            else:
                lines.append(
                    f"[bold]{row.label}[/]  "
                    f"Used: {fmt_mb(row.used_mb)}"
                )

        container.update("\n".join(lines))
