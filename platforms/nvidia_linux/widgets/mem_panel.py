"""Memory Panel — system RAM and swap from MemoryStats."""
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
        border: solid yellow;
        border-title-color: yellow;
        padding: 0 1;
        height: auto;
    }
    MemPanel Static { height: 1; }
    """

    mem_stats: reactive[MemoryStats | None] = reactive(None)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "Memory"

    def compose(self) -> ComposeResult:
        yield Static(id="mem-rows")

    def watch_mem_stats(self, _: MemoryStats | None) -> None:
        mem = self.mem_stats
        container = self.query_one("#mem-rows", Static)

        if mem is None or not mem.available or not mem.rows:
            container.update("[dim]No memory data[/]")
            return

        lines: list[str] = []
        for row in mem.rows:
            if row.total_mb is not None and row.total_mb > 0:
                lines.append(
                    f"[bold]{row.label}[/]  {fmt_mb(row.used_mb)}/{fmt_mb(row.total_mb)}  "
                    f"{row.pct:.1f}%"
                )
            else:
                lines.append(f"[bold]{row.label}[/]  {fmt_mb(row.used_mb)}")
        container.update("\n".join(lines))
