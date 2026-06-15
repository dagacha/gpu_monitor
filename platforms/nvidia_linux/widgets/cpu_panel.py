"""CPU Panel — per-core load bars, two-column layout."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from common.types import CPUStats
from common.widgets.util import bar, fmt_watts

_BAR_W = 18
_MAX_CORES = 32


def _fmt_core(core) -> str:
    return (
        f"[dim]#{core.index:<3}[/] "
        f"{bar(core.load_pct, width=_BAR_W, show_pct=False)}"
        f" {core.load_pct:4.1f}%"
    )


class CPUPanel(Widget):
    DEFAULT_CSS = """
    CPUPanel {
        border: solid blue;
        border-title-color: blue;
        padding: 0 1;
        height: auto;
    }
    CPUPanel #cpu-header { height: 1; color: $text-muted; margin-bottom: 1; }
    CPUPanel .cpu-row { height: 1; layout: horizontal; }
    CPUPanel .cpu-col { width: 1fr; }
    """

    cpu_stats: reactive[CPUStats | None] = reactive(None)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "CPU Cores"

    def compose(self) -> ComposeResult:
        yield Static("", id="cpu-header")
        half = _MAX_CORES // 2
        for i in range(half):
            with Static(classes="cpu-row", id=f"cpu-row-{i}"):
                yield Static("", classes="cpu-col", id=f"cpu-left-{i}")
                yield Static("", classes="cpu-col", id=f"cpu-right-{i}")

    def watch_cpu_stats(self, _: CPUStats | None) -> None:
        cpu = self.cpu_stats
        if cpu is None:
            return

        # Header
        parts: list[str] = []
        if cpu.temp_c is not None:
            parts.append(f"Temp: {cpu.temp_c:.0f}°C")
        if cpu.power_w is not None:
            parts.append(f"Pkg: {fmt_watts(cpu.power_w)}")
        parts.append(f"Total: {cpu.total_load_pct:.1f}%")
        parts.append(f"Cores: {len(cpu.cores)}")
        self.query_one("#cpu-header", Static).update("  |  ".join(parts))

        cores = cpu.cores
        half = (len(cores) + 1) // 2
        max_rows = _MAX_CORES // 2

        for i in range(max_rows):
            left = self.query_one(f"#cpu-left-{i}", Static)
            right = self.query_one(f"#cpu-right-{i}", Static)
            row = self.query_one(f"#cpu-row-{i}", Static)

            if i < half and i < len(cores):
                left.update(_fmt_core(cores[i]))
                right_idx = i + half
                right.update(_fmt_core(cores[right_idx]) if right_idx < len(cores) else "")
                row.display = True
            else:
                row.display = False
