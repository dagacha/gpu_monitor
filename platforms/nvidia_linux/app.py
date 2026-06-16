"""
gpu_monitor — htop-like GPU/CPU monitor for NVIDIA GPUs on Linux.

Uses nvidia-smi for GPU metrics and psutil for CPU/memory/processes.

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
from common.logger import CSVLogger

from platforms.nvidia_linux.collectors import NvidiaLinuxCollectors
from platforms.nvidia_linux.config import NvidiaConfig
from platforms.nvidia_linux.widgets import CPUPanel, GPUPanel, MemPanel, ProcessTable


class NvidiaLinuxMonitorApp(BaseMonitorApp):
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

    TITLE = "GPU Monitor — NVIDIA Linux"
    SUB_TITLE = "Linux  |  nvidia-smi"

    def __init__(self, config: MonitorConfig | None = None) -> None:
        super().__init__(config or NvidiaConfig())
        self._collectors = NvidiaLinuxCollectors(self.config)

    def compose(self):
        yield Header()

        with Static(id="top-row"):
            yield GPUPanel(id="gpu-panel")
            with Static(id="right-col"):
                yield MemPanel(id="mem-panel")

        yield ProcessTable(id="process-table")
        yield CPUPanel(id="cpu-panel")
        yield Static("", id="status-bar")
        yield Footer()


if __name__ == "__main__":
    NvidiaLinuxMonitorApp().run()
