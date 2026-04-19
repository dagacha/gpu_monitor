"""
CPU Panel — per-core load + effective clock from LibreHardwareMonitor.
Uses shared common.types and widgets.util.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from common.types import CPUStats
from common.widgets.util import bar, fmt_watts

_BAR_W = 18
_MAX_CORES = 32  # pre-allocate enough rows for any core count


def _clk(mhz: float | None) -> str:
    """Format clock speed."""
    if mhz is None:
        return "        "
    if mhz >= 1000:
        return f"{mhz / 1000:4.2f}GHz"
    return f" {mhz:4.0f}MHz"


def _fmt_core(cpu, idx: int) -> str:
    """Format a single core row."""
    if idx >= len(cpu.cores):
        return ""
    c = cpu.cores[idx]
    return f"[dim]#{c.index:<2}[/] {bar(c.load_pct, width=_BAR_W, show_pct=False)} {_clk(c.eff_clock_mhz)} {c.load_pct:4.1f}%"


class CPUPanel(Widget):
    DEFAULT_CSS = """
    CPUPanel {
        border: solid $accent;
        border-title-color: $accent;
        padding: 0 1;
        height: auto;
    }
    CPUPanel #cpu-header { height: 1; color: $text-muted; margin-bottom: 1; }
    CPUPanel .cpu-row   { height: 1; layout: horizontal; }
    CPUPanel .cpu-col   { width: 1fr; }
    """

    cpu_stats: reactive[CPUStats | None] = reactive(None)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "CPU Cores"

    def compose(self) -> ComposeResult:
        yield Static("", id="cpu-header")
        # Pre-allocate _MAX_CORES/2 rows (two cores per row, two columns)
        for i in range(_MAX_CORES // 2):
            with Static(classes="cpu-row", id=f"cpu-row-{i}"):
                yield Static("", classes="cpu-col", id=f"cpu-left-{i}")
                yield Static("", classes="cpu-col", id=f"cpu-right-{i}")

    def on_mount(self) -> None:
        self._update()

    def watch_cpu_stats(self, _: CPUStats | None) -> None:
        self._update()

    def _update(self) -> None:
        cpu = self.cpu_stats

        # Header
        parts = []
        if cpu and cpu.temp_c is not None:
            parts.append(f"Temp: {cpu.temp_c:.0f}°C")
        if cpu and cpu.power_w is not None:
            parts.append(f"Pkg: {fmt_watts(cpu.power_w)}")
        if cpu and cpu.total_load_pct is not None:
            parts.append(f"Total: {cpu.total_load_pct:.1f}%")
        
        self.query_one("#cpu-header", Static).update(
            "  |  ".join(parts) if parts else "CPU sensors unavailable"
        )

        cores = cpu.cores if cpu else []
        half = (len(cores) + 1) // 2

        for i in range(_MAX_CORES // 2):
            left = self.query_one(f"#cpu-left-{i}", Static)
            right = self.query_one(f"#cpu-right-{i}", Static)
            row = self.query_one(f"#cpu-row-{i}", Static)

            if i < half:
                left.update(_fmt_core(cpu, i) if cpu else "")
                right_idx = i + half
                right.update(_fmt_core(cpu, right_idx) if cpu and right_idx < len(cores) else "")
                row.display = True
            else:
                row.display = False
