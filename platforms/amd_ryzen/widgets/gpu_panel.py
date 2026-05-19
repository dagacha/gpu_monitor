"""
GPU Panel — engine utilization bars, 60s sparkline, temps, clocks, power.
Uses shared common.types and widgets.util.
"""
from __future__ import annotations

from collections import deque

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Sparkline, Static

from common.types import GPUStats
from common.widgets.util import bar, fmt_watts

_HISTORY_LEN = 60
_ENGINE_ORDER = ["3D", "Compute", "Copy", "Video", "Security", "Timer"]
_BAR_WIDTH = 28


class GPUPanel(Widget):
    DEFAULT_CSS = """
    GPUPanel {
        border: solid $accent;
        border-title-color: $accent;
        padding: 0 1;
        height: auto;
    }
    GPUPanel .engine-row { height: 1; }
    GPUPanel #sparkline-label {
        color: $text-muted;
        margin-top: 1;
    }
    GPUPanel Sparkline {
        height: 3;
        margin-bottom: 1;
    }
    GPUPanel #hw-row { height: 1; margin-top: 1; }
    GPUPanel #soc-row { height: 1; color: $text-muted; }
    GPUPanel #status-label { height: 1; }
    """

    gpu_stats: reactive[GPUStats | None] = reactive(None)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._history: deque[float] = deque([0.0] * _HISTORY_LEN, maxlen=_HISTORY_LEN)
        self.border_title = "GPU  (AMD Radeon)"

    def compose(self) -> ComposeResult:
        yield Label("Total Utilization — 60s history", id="sparkline-label")
        yield Sparkline(data=list(self._history), summary_function=max, id="gpu-sparkline")
        for engine in _ENGINE_ORDER:
            yield Static(
                f"[dim]{engine:<13}[/] {'░' * _BAR_WIDTH}   0.0%",
                id=f"engine-{engine}",
                classes="engine-row",
            )
        yield Static("", id="hw-row")
        yield Static("", id="soc-row")
        yield Label("", id="status-label")

    def on_mount(self) -> None:
        self._update_hw_rows()

    # ------------------------------------------------------------------

    def _lhm_pct(self, engine: str) -> float | None:
        """Get utilization from engines dict, with prefix matching."""
        hw = self.gpu_stats
        if not hw or not hw.engines:
            return None
        if engine in hw.engines:
            return hw.engines[engine]
        # prefix match: "Compute" matches "Compute 0"
        for k, v in hw.engines.items():
            if k.startswith(engine) or engine.startswith(k.split()[0]):
                return v
        return None

    def _update_engine_bars(self) -> None:
        gpu = self.gpu_stats
        if gpu is None:
            return

        for engine in _ENGINE_ORDER:
            pct = self._lhm_pct(engine) or 0.0
            self.query_one(f"#engine-{engine}", Static).update(
                f"[dim]{engine:<13}[/] {bar(pct, width=_BAR_WIDTH)}"
            )

    def _update_hw_rows(self) -> None:
        gpu = self.gpu_stats
        if gpu is None:
            return

        # Always render Temp so its absence is visible (rather than the row
        # quietly disappearing). LHM doesn't expose a temp sensor for Strix
        # Halo's iGPU; the D3DKMT collector fills it when possible.
        temp_str = f"{gpu.temp_c:.0f}°C" if gpu.temp_c is not None else "--"
        parts = [f"Temp: {temp_str}"]
        if gpu.clock_mhz is not None:
            parts.append(f"Core: {gpu.clock_mhz:.0f} MHz")
        if gpu.memory_clock_mhz is not None:
            parts.append(f"Mem: {gpu.memory_clock_mhz:.0f} MHz")
        if gpu.power_w is not None:
            parts.append(f"Power: {fmt_watts(gpu.power_w)}")

        self.query_one("#hw-row", Static).update("  |  ".join(parts))

    def watch_gpu_stats(self, stats: GPUStats | None) -> None:
        if stats is None:
            return
        
        status_label = self.query_one("#status-label", Label)
        if not stats.available:
            status_label.update("[red]GPU counters unavailable[/]")
            return
        status_label.update("")

        # Update sparkline
        self._history.append(stats.total_utilization)
        self.query_one("#gpu-sparkline", Sparkline).data = list(self._history)

        # Update engine bars and hardware sensor row
        self._update_engine_bars()
        self._update_hw_rows()

    def reset_history(self) -> None:
        """Reset sparkline history to zeros."""
        self._history = deque([0.0] * _HISTORY_LEN, maxlen=_HISTORY_LEN)
        self.query_one("#gpu-sparkline", Sparkline).data = list(self._history)
