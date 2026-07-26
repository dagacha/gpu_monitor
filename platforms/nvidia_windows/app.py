"""
gpu_monitor — htop-like GPU/CPU monitor for NVIDIA GPUs on Windows.

Uses NVML (pynvml) for GPU metrics, Windows PDH for per-process GPU
memory/utilization, and psutil for CPU/memory. Falls back to nvidia-smi
when NVML or PDH is unavailable.

Keyboard shortcuts:
    q / Ctrl+C   Quit
    p            Pause / resume
    r            Reset sparkline history
    v            Toggle process table
    c            Toggle CPU panel
    l            Toggle CSV logging
"""
from __future__ import annotations

import os
from typing import ClassVar

from textual.binding import Binding
from textual.widgets import Footer, Header, Static

from common.base_app import BaseMonitorApp
from common.config import MonitorConfig

from platforms.nvidia_windows.collectors import NvidiaWindowsCollectors
from platforms.nvidia_windows.config import NvidiaConfig
from platforms.nvidia_windows.widgets import CPUPanel, GPUPanel, MemPanel, ProcessTable


class NvidiaWindowsMonitorApp(BaseMonitorApp):
    CSS = """
    Screen {
        layout: vertical;
    }
    #top-row {
        layout: horizontal;
        height: auto;
    }
    #top-row GPUPanel {
        width: 2fr;
    }
    #top-row #right-col {
        width: 1fr;
        layout: vertical;
    }
    #status-bar {
        height: 1;
        background: $panel;
        color: $text-muted;
        padding: 0 1;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = BaseMonitorApp.BASE_BINDINGS

    TITLE = "GPU Monitor — NVIDIA Windows"
    SUB_TITLE = "Windows  |  NVML + PDH"

    def __init__(self, config: MonitorConfig | None = None) -> None:
        super().__init__(config or NvidiaConfig())
        self._collectors = NvidiaWindowsCollectors(self.config)

    def _on_close(self) -> None:
        self._collectors.close()

    def compose(self):
        yield Header()

        with Static(id="top-row"):
            yield GPUPanel(gpu_name=self._collectors.gpu_name, id="gpu-panel")
            with Static(id="right-col"):
                yield MemPanel(id="mem-panel")

        yield ProcessTable(id="process-table")
        yield CPUPanel(id="cpu-panel")
        yield Static("", id="status-bar")
        yield Footer()

    def action_toggle_logging(self) -> None:
        """Match legacy NVIDIA Windows subtitle style (no bullet on REC)."""
        msg = self._csv.toggle()
        if self._csv.active:
            self.sub_title = f"REC  {os.path.basename(self._csv.path)}"
        else:
            self.sub_title = self._default_subtitle()
        self._set_status(msg)


if __name__ == "__main__":
    NvidiaWindowsMonitorApp().run()
