"""
Process Table for Apple Silicon.
Shows top CPU processes via psutil.
Note: macOS has no public API for per-process GPU memory.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from common.types import ProcessInfo, ProcessStats
from common.widgets.util import fmt_mb


class ProcessTable(Widget):
    DEFAULT_CSS = """
    ProcessTable {
        border: solid $accent;
        border-title-color: $accent;
        padding: 0 1;
        height: auto;
    }
    ProcessTable #pt-header {
        height: 1;
        color: $text-muted;
    }
    ProcessTable .pt-row {
        height: 1;
    }
    """

    MAX_ROWS = 12
    process_stats: reactive[ProcessStats | None] = reactive(None)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "Top Processes (by CPU)"

    def compose(self) -> ComposeResult:
        yield Static(self._header(), id="pt-header")
        for i in range(self.MAX_ROWS):
            yield Static("", classes="pt-row", id=f"pt-row-{i}")

    @staticmethod
    def _header() -> str:
        return (
            f"{'PID':>7}  {'Process':<25}  {'Memory':>10}"
        )

    def _fmt_mem(self, mb: float) -> str:
        """Format memory to human readable."""
        if mb == 0:
            return "    --   "
        return f"{mb:6.1f} MB"

    def watch_process_stats(self, stats: ProcessStats | None) -> None:
        procs = stats.processes if stats else []
        
        for i in range(self.MAX_ROWS):
            row = self.query_one(f"#pt-row-{i}", Static)
            if i < len(procs):
                p = procs[i]
                row.update(
                    f"{p.pid:>7}  {p.name[:25]:<25}  "
                    f"{self._fmt_mem(p.total_mb):>10}"
                )
            else:
                row.update("")
