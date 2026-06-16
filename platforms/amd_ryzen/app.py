"""
gpu_monitor — htop-like GPU/CPU/NPU monitor for AMD Ryzen AI Max on Windows 11.
Uses shared common.types and platform-specific widgets.

Keyboard shortcuts:
    q / Ctrl+C   Quit
    p            Pause / resume
    r            Reset sparkline history
    v            Toggle process table visibility
    c            Toggle CPU panel visibility
    l            Toggle CSV logging
"""
from __future__ import annotations

import os
import subprocess
from typing import Any, ClassVar

from textual.binding import Binding
from textual.widgets import Footer, Header, Static

from common.base_app import BaseMonitorApp
from common.config import MonitorConfig
from common.types import SystemSnapshot

from platforms.amd_ryzen.collectors import AMDRyzenCollectors
from platforms.amd_ryzen.collectors.npu import NPUStats
from platforms.amd_ryzen.config import AMDConfig
from platforms.amd_ryzen.widgets import (
    CPUPanel,
    GPUPanel,
    MemPanel,
    NPUPanel,
    PowerPanel,
    ProcessTable,
)


def _ensure_lhm() -> None:
    """Launch LHM in the background if it is not already running."""
    try:
        import psutil
        for proc in psutil.process_iter(["name"]):
            if proc.info["name"] == "LibreHardwareMonitor.exe":
                return  # already running
    except Exception:
        pass
    if os.path.isfile(AMDConfig.LHM_EXE):
        try:
            subprocess.Popen(
                [AMDConfig.LHM_EXE],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception:
            pass


class AMDRyzenMonitorApp(BaseMonitorApp):
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

    TITLE = "GPU Monitor — AMD Ryzen AI Max"
    SUB_TITLE = "Windows 11  |  UMA Architecture"

    def __init__(self, config: MonitorConfig | None = None) -> None:
        _ensure_lhm()
        super().__init__(config or AMDConfig())
        self._collectors = AMDRyzenCollectors()
        # Cache the last NPU sample so widget updates outside _tick can
        # still inspect it.
        self._last_npu: NPUStats | None = None

    def compose(self):
        yield Header()

        with Static(id="top-row"):
            yield GPUPanel(id="gpu-panel")
            with Static(id="right-col"):
                yield NPUPanel(id="npu-panel")
                yield MemPanel(id="mem-panel")

        yield ProcessTable(id="process-table")
        yield PowerPanel(id="power-panel")
        yield CPUPanel(id="cpu-panel")
        yield Static("", id="status-bar")
        yield Footer()

    def _update_extra_widgets(
        self, snapshot: SystemSnapshot, extra: Any
    ) -> None:
        """AMD-specific: push NPU stats to the NPU panel."""
        self._last_npu = extra
        if extra is None:
            return
        try:
            self.query_one("#npu-panel").npu_stats = extra
        except Exception:
            # Panel not present — should not happen, but be defensive.
            pass

    def _on_close(self) -> None:
        """Release platform-specific resources (LHM DLL + collectors)."""
        if self._collectors is not None:
            try:
                self._collectors.close()
            except Exception:
                pass


if __name__ == "__main__":
    AMDRyzenMonitorApp().run()
