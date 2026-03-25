"""
Memory Panel — shows GPU dedicated memory (LHM), GPU shared memory,
and system RAM. All drawn from the 128 GB UMA pool.
"""
from __future__ import annotations

import psutil

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Static

from collectors.hw_monitor import HWSensorData


def _fmt_mb(mb: float) -> str:
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{mb:.0f} MB"


def _bar(pct: float, width: int = 28) -> str:
    filled = int(pct / 100 * width)
    empty = width - filled
    color = "red" if pct >= 80 else "yellow" if pct >= 50 else "green"
    return f"[{color}]{'█' * filled}{'░' * empty}[/] {pct:5.1f}%"


class MemPanel(Widget):
    DEFAULT_CSS = """
    MemPanel {
        border: solid $accent;
        border-title-color: $accent;
        padding: 0 1;
        height: auto;
    }
    MemPanel Static {
        height: 1;
    }
    MemPanel #mem-note {
        color: $text-muted;
        margin-top: 1;
    }
    """

    hw_stats: reactive[HWSensorData | None] = reactive(None)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "Memory  (128 GB UMA)"

    def compose(self) -> ComposeResult:
        yield Static("", id="sys-row")
        yield Static("", id="gpu-ded-row")
        yield Static("", id="gpu-shared-row")
        yield Static("[dim]GPU dedicated + shared drawn from same 128 GB UMA pool[/]", id="mem-note")

    def on_mount(self) -> None:
        self._refresh()

    def watch_hw_stats(self, _: HWSensorData | None) -> None:
        self._refresh()

    def _refresh(self) -> None:
        hw = self.hw_stats
        vm = psutil.virtual_memory()

        # System RAM
        sys_pct = vm.percent
        sys_used = vm.used / 1024**2  # MB
        sys_total = vm.total / 1024**2
        self.query_one("#sys-row", Static).update(
            f"[dim]System RAM    [/]{_bar(sys_pct)}  {_fmt_mb(sys_used)} / {_fmt_mb(sys_total)}"
        )

        # GPU dedicated (from LHM)
        if hw and hw.gpu_mem_used_mb is not None and hw.gpu_mem_total_mb is not None:
            used = hw.gpu_mem_used_mb
            total = hw.gpu_mem_total_mb
            pct = min(used / total * 100, 100) if total > 0 else 0
            self.query_one("#gpu-ded-row", Static).update(
                f"[dim]GPU Dedicated  [/]{_bar(pct)}  {_fmt_mb(used)} / {_fmt_mb(total)}"
            )
        else:
            self.query_one("#gpu-ded-row", Static).update(
                "[dim]GPU Dedicated  [/] --"
            )

        # GPU shared (from LHM)
        if hw and hw.gpu_mem_shared_mb is not None:
            used = hw.gpu_mem_shared_mb
            total = hw.gpu_mem_shared_total_mb or 16384.0
            pct = min(used / total * 100, 100) if total > 0 else 0
            self.query_one("#gpu-shared-row", Static).update(
                f"[dim]GPU Shared     [/]{_bar(pct)}  {_fmt_mb(used)} / {_fmt_mb(total)}"
            )
        else:
            self.query_one("#gpu-shared-row", Static).update(
                "[dim]GPU Shared     [/] --"
            )
