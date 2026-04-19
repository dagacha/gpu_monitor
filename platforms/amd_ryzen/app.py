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

import asyncio
import os
import subprocess
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Label, Static

from common.config import MonitorConfig
from common.logger import CSVLogger
from common.types import PowerStats, SystemSnapshot
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


class AMDRyzenMonitorApp(App):
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

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "Quit"),
        Binding("p", "toggle_pause", "Pause"),
        Binding("r", "reset_history", "Reset"),
        Binding("v", "toggle_processes", "Processes"),
        Binding("c", "toggle_cpu", "CPU Panel"),
        Binding("l", "toggle_logging", "Log CSV"),
    ]

    TITLE = "GPU Monitor — AMD Ryzen AI Max"
    SUB_TITLE = "Windows 11  |  UMA Architecture"

    def __init__(self, config: AMDConfig | None = None) -> None:
        super().__init__()
        _ensure_lhm()
        
        self.config = config or AMDConfig()
        self._collectors = AMDRyzenCollectors()
        self._csv = CSVLogger(log_dir=self.config.log_dir)
        
        self._paused = False
        self._show_processes = True
        self._show_cpu = True
        
        # Cache for logging
        self._last_snapshot: SystemSnapshot | None = None
        self._last_npu: NPUStats | None = None

    def compose(self) -> ComposeResult:
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

    def on_mount(self) -> None:
        self.set_interval(self.config.refresh_interval, self._tick)
        self._set_status("Ready — press ? for help")

    async def _tick(self) -> None:
        if self._paused:
            return

        loop = asyncio.get_event_loop()
        snapshot, npu = await loop.run_in_executor(None, self._collectors.collect)

        self._last_snapshot = snapshot
        self._last_npu = npu

        # Push to widgets
        self.query_one("#gpu-panel", GPUPanel).gpu_stats = snapshot.gpu
        self.query_one("#npu-panel", NPUPanel).npu_stats = npu
        self.query_one("#mem-panel", MemPanel).mem_stats = snapshot.memory
        self.query_one("#process-table", ProcessTable).process_stats = snapshot.processes
        self.query_one("#power-panel", PowerPanel).power_stats = snapshot.power
        self.query_one("#cpu-panel", CPUPanel).cpu_stats = snapshot.cpu

        # CSV logging
        if self._csv.active:
            self._csv.log(snapshot)

    def action_toggle_pause(self) -> None:
        self._paused = not self._paused
        if self._paused:
            self.sub_title = "PAUSED — press p to resume"
            self._set_status("Paused")
        else:
            self.sub_title = "Windows 11  |  UMA Architecture"
            self._set_status("Resumed")

    def action_reset_history(self) -> None:
        panel = self.query_one("#gpu-panel", GPUPanel)
        panel.reset_history()
        self._set_status("Sparkline history reset")

    def action_toggle_processes(self) -> None:
        self._show_processes = not self._show_processes
        pt = self.query_one("#process-table", ProcessTable)
        pt.display = self._show_processes
        self._set_status(
            "Process table shown" if self._show_processes else "Process table hidden"
        )

    def action_toggle_cpu(self) -> None:
        self._show_cpu = not self._show_cpu
        cp = self.query_one("#cpu-panel", CPUPanel)
        cp.display = self._show_cpu
        self._set_status(
            "CPU panel shown" if self._show_cpu else "CPU panel hidden"
        )

    def action_toggle_logging(self) -> None:
        msg = self._csv.toggle()
        if self._csv.active:
            self.sub_title = f"● REC  {os.path.basename(self._csv.path)}"
        else:
            self.sub_title = "Windows 11  |  UMA Architecture"
        self._set_status(msg)

    def _set_status(self, msg: str) -> None:
        self.query_one("#status-bar", Static).update(msg)

    def on_unmount(self) -> None:
        self._collectors.close()
        if self._csv.active:
            self._csv.stop()


if __name__ == "__main__":
    AMDRyzenMonitorApp().run()
