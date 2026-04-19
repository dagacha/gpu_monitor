"""
GPU Panel — engine utilization bars, 60s sparkline, temps, clocks, power.
Prefers LHM D3D load data; falls back to PDH counters.
"""
from __future__ import annotations

from collections import deque
from typing import Optional

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Sparkline, Static

from collectors.gpu_pdh import GPUStats
from collectors.hw_monitor import HWSensorData
from widgets.util import bar

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
    hw_stats: reactive[HWSensorData | None] = reactive(None)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._history: deque[float] = deque([0.0] * _HISTORY_LEN, maxlen=_HISTORY_LEN)
        self.border_title = "GPU  (AMD Radeon 8060S / RDNA)"

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

    def _lhm_pct(self, engine: str) -> Optional[float]:
        hw = self.hw_stats
        if not hw or not hw.d3d_loads:
            return None
        if engine in hw.d3d_loads:
            return hw.d3d_loads[engine]
        # prefix match: "Compute" matches "Compute 0"
        for k, v in hw.d3d_loads.items():
            if k.startswith(engine) or engine.startswith(k.split()[0]):
                return v
        return None

    def _update_engine_bars(self, pdh_stats: GPUStats | None) -> None:
        pdh = {e.name: e.utilization for e in (pdh_stats.engines if pdh_stats else [])}
        for engine in _ENGINE_ORDER:
            pct = self._lhm_pct(engine)
            if pct is None:
                pct = pdh.get(engine, 0.0)
            self.query_one(f"#engine-{engine}", Static).update(
                f"[dim]{engine:<13}[/] {bar(pct, width=_BAR_WIDTH)}"
            )

    def _update_hw_rows(self) -> None:
        hw = self.hw_stats
        if hw is None:
            return

        parts = []
        if hw.gpu_temp_c is not None:
            parts.append(f"Temp: {hw.gpu_temp_c:.0f}°C")
        if hw.gpu_clock_mhz is not None:
            parts.append(f"Core: {hw.gpu_clock_mhz:.0f} MHz")
        if hw.gpu_memory_clock_mhz is not None:
            parts.append(f"Mem: {hw.gpu_memory_clock_mhz:.0f} MHz")
        if hw.gpu_soc_clock_mhz is not None:
            parts.append(f"SoC: {hw.gpu_soc_clock_mhz:.0f} MHz")
        if hw.gpu_power_w is not None:
            parts.append(f"GPU Pwr: {hw.gpu_power_w:.1f} W")
        self.query_one("#hw-row", Static).update(
            "  |  ".join(parts) if parts else "Sensors: -- (LHM not available)"
        )

        # SoC total row
        soc_parts = []
        if hw.cpu_temp_c is not None:
            soc_parts.append(f"CPU Temp: {hw.cpu_temp_c:.0f}°C")
        if hw.cpu_power_w is not None:
            soc_parts.append(f"CPU Pkg: {hw.cpu_power_w:.0f} W")
        if hw.soc_power_w is not None:
            soc_parts.append(f"[bold]SoC Total: {hw.soc_power_w:.1f} W[/]")
        self.query_one("#soc-row", Static).update("  |  ".join(soc_parts))

    def watch_gpu_stats(self, stats: GPUStats | None) -> None:
        if stats is None:
            return
        status = self.query_one("#status-label", Label)
        if not stats.available:
            status.update("[red]GPU counters unavailable — install pywin32 and AMD drivers[/]")
            return
        status.update("")

        # Use LHM GPU core load for sparkline if available, else PDH total
        hw = self.hw_stats
        total = hw.gpu_core_load_pct if (hw and hw.gpu_core_load_pct is not None) else stats.total_utilization
        self._history.append(total)
        self.query_one("#gpu-sparkline", Sparkline).data = list(self._history)
        self._update_engine_bars(stats)

    def watch_hw_stats(self, _: HWSensorData | None) -> None:
        self._update_hw_rows()
        # Re-render engine bars with fresh LHM data
        self._update_engine_bars(self.gpu_stats)
