"""GPU Panel — utilization sparkline, bars, temp/clocks/power/fan/PCIe."""
from __future__ import annotations

from collections import deque

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Sparkline, Static

from common.types import GPUStats
from common.widgets.util import bar, fmt_mb, fmt_watts

_HISTORY_LEN = 60
_BAR_W = 28


class GPUPanel(Widget):
    DEFAULT_CSS = """
    GPUPanel {
        border: solid green;
        border-title-color: green;
        padding: 0 1;
        height: auto;
    }
    GPUPanel .sparkline-label { color: $text-muted; }
    GPUPanel Sparkline { height: 3; margin-bottom: 1; }
    GPUPanel .engine-row { height: 1; }
    GPUPanel .hw-row { height: 1; margin-top: 1; }
    """

    gpu_stats: reactive[GPUStats | None] = reactive(None)

    def __init__(self, gpu_name: str = "NVIDIA", **kwargs) -> None:
        super().__init__(**kwargs)
        self._history: deque[float] = deque([0.0] * _HISTORY_LEN, maxlen=_HISTORY_LEN)
        self.border_title = f"GPU  ({gpu_name})"

    def compose(self) -> ComposeResult:
        yield Label("GPU Utilization — 60s history", id="sparkline-label", classes="sparkline-label")
        yield Sparkline(data=list(self._history), summary_function=max, id="gpu-sparkline")
        yield Static("", id="gpu-util-bar", classes="engine-row")
        yield Static("", id="mem-util-bar", classes="engine-row")
        yield Static("", id="hw-row", classes="hw-row")

    def watch_gpu_stats(self, stats: GPUStats | None) -> None:
        if stats is None:
            return

        if not stats.available:
            self.query_one("#hw-row", Static).update("[red]nvidia-smi unavailable[/]")
            return

        # Sparkline
        self._history.append(stats.total_utilization)
        self.query_one("#gpu-sparkline", Sparkline).data = list(self._history)

        # Engine bars
        eng = stats.engines
        self.query_one("#gpu-util-bar", Static).update(
            f"[dim]GPU     [/] {bar(eng.get('3D', stats.total_utilization), width=_BAR_W)}"
        )
        self.query_one("#mem-util-bar", Static).update(
            f"[dim]Mem BW  [/] {bar(eng.get('Memory BW', 0.0), width=_BAR_W)}"
        )

        # Hardware row
        parts: list[str] = []
        if stats.temp_c is not None:
            parts.append(f"Temp: {stats.temp_c:.0f}°C")
        if stats.clock_mhz is not None:
            parts.append(f"Core: {stats.clock_mhz / 1000:.2f} GHz")
        if stats.memory_clock_mhz is not None:
            parts.append(f"Mem: {stats.memory_clock_mhz:.0f} MHz")
        if stats.power_w is not None:
            parts.append(f"Pwr: {fmt_watts(stats.power_w)}")
        if stats.mem_used_mb is not None and stats.mem_total_mb is not None:
            parts.append(f"VRAM: {fmt_mb(stats.mem_used_mb)}/{fmt_mb(stats.mem_total_mb)}")
        self.query_one("#hw-row", Static).update("  |  ".join(parts))

    def reset_history(self) -> None:
        self._history = deque([0.0] * _HISTORY_LEN, maxlen=_HISTORY_LEN)
        self.query_one("#gpu-sparkline", Sparkline).data = list(self._history)
