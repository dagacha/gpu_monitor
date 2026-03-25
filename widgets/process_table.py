"""
Process Table — top GPU memory consumers, refreshed every 5 seconds.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from collectors.process_gpu import ProcessGPUStat


def _fmt_bytes(b: int) -> str:
    if b == 0:
        return "    --   "
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:6.1f} {unit}"
        b /= 1024
    return f"{b:6.1f} TB"


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
    processes: reactive[list[ProcessGPUStat]] = reactive(list)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "GPU Processes  (top by memory, refreshes every 5s)"

    def compose(self) -> ComposeResult:
        yield Static(self._header(), id="pt-header")
        for i in range(self.MAX_ROWS):
            yield Static("", classes="pt-row", id=f"pt-row-{i}")

    @staticmethod
    def _header() -> str:
        return (
            f"{'PID':>7}  {'Process':<25}  {'Local':>10}  {'Shared':>10}  {'Total':>10}"
        )

    def watch_processes(self, procs: list[ProcessGPUStat]) -> None:
        for i in range(self.MAX_ROWS):
            row = self.query_one(f"#pt-row-{i}", Static)
            if i < len(procs):
                p = procs[i]
                row.update(
                    f"{p.pid:>7}  {p.name[:25]:<25}  "
                    f"{_fmt_bytes(p.local_bytes):>10}  "
                    f"{_fmt_bytes(p.shared_bytes):>10}  "
                    f"{_fmt_bytes(p.total_bytes):>10}"
                )
            else:
                row.update("")
