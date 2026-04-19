"""
GPU Panel for Apple Silicon.
Shows GPU utilization, frequency, and power from powermetrics.
"""
from __future__ import annotations

from collections import deque

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Sparkline, Static

from common.types import GPUStats
from common.widgets.util import bar, fmt_watts, fmt_hz

_HISTORY_LEN = 60
_BAR_WIDTH = 28


class GPUPanel(Widget):
    DEFAULT_CSS = """
    GPUPanel {
        border: solid $accent;
        border-title-color: $accent;
        padding: 0 1;
        height: auto;
    }
    GPUPanel #sparkline-label {
        color: $text-muted;
        margin-top: 1;
    }
    GPUPanel Sparkline {
        height: 3;
        margin-bottom: 1;
    }
    GPUPanel #hw-row { height: 1; margin-top: 1; }
    GPUPanel #status-label { height: 1; }
    """

    gpu_stats: reactive[GPUStats | None] = reactive(None)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._history: deque[float] = deque([0.0] * _HISTORY_LEN, maxlen=_HISTORY_LEN)
        self.border_title = "GPU  (Apple Silicon)"

    def compose(self) -> ComposeResult:
        yield Label("Active % — 60s history", id="sparkline-label")
        yield Sparkline(data=list(self._history), summary_function=max, id="gpu-sparkline")
        yield Static("", id="hw-row")
        yield Label("", id="status-label")

    def on_mount(self) -> None:
        self._update_hw_row()

    def _update_hw_row(self) -> None:
        gpu = self.gpu_stats
        if gpu is None:
            return

        parts = []
        if gpu.clock_mhz is not None:
            parts.append(f"Freq: {fmt_hz(gpu.clock_mhz * 1e6)}")
        if gpu.power_w is not None:
            parts.append(f"Power: {fmt_watts(gpu.power_w)}")

        status = "GPU data unavailable (run with sudo)" if not parts else "  |  ".join(parts)
        self.query_one("#hw-row", Static).update(status)

    def watch_gpu_stats(self, stats: GPUStats | None) -> None:
        if stats is None:
            return

        status_label = self.query_one("#status-label", Label)
        if not stats.available:
            status_label.update("[dim]GPU data requires sudo powermetrics[/]")
            return
        status_label.update("")

        # Update sparkline
        self._history.append(stats.total_utilization)
        self.query_one("#gpu-sparkline", Sparkline).data = list(self._history)

        # Update hardware row
        self._update_hw_row()

    def reset_history(self) -> None:
        """Reset sparkline history to zeros."""
        self._history = deque([0.0] * _HISTORY_LEN, maxlen=_HISTORY_LEN)
        self.query_one("#gpu-sparkline", Sparkline).data = list(self._history)
