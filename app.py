"""
gpu_monitor — htop-like GPU/CPU/NPU monitor for AMD Ryzen AI Max 395 on Windows 11.

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
import subprocess
import os
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Label, Static

from collectors.gpu_pdh import GPUPDHCollector
from collectors.hw_monitor import HWMonitorCollector
from collectors.npu import NPUCollector
from collectors.process_gpu import ProcessGPUCollector
from logger import CSVLogger
from widgets.cpu_panel import CPUPanel
from widgets.gpu_panel import GPUPanel
from widgets.mem_panel import MemPanel
from widgets.npu_panel import NPUPanel
from widgets.process_table import ProcessTable

REFRESH_INTERVAL = 1.0
_LHM_EXE = r"C:\Users\Office\LibreHardwareMonitor\LibreHardwareMonitor.exe"


def _ensure_lhm() -> None:
    """Launch LHM in the background if it is not already running."""
    try:
        import psutil
        for proc in psutil.process_iter(["name"]):
            if proc.info["name"] == "LibreHardwareMonitor.exe":
                return  # already running
    except Exception:
        pass
    if os.path.isfile(_LHM_EXE):
        try:
            subprocess.Popen(
                [_LHM_EXE],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception:
            pass


class GPUMonitorApp(App):
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

    TITLE = "GPU Monitor — AMD Ryzen AI Max 395"
    SUB_TITLE = "Windows 11  |  128 GB UMA"

    def __init__(self) -> None:
        super().__init__()
        _ensure_lhm()
        self._pdh = GPUPDHCollector()
        self._hw = HWMonitorCollector()
        self._npu = NPUCollector()
        self._proc = ProcessGPUCollector()
        self._csv = CSVLogger()
        self._paused = False
        self._show_processes = True
        self._show_cpu = True

        # Cache last stats for logger
        self._last_gpu = None
        self._last_hw = None
        self._last_npu = None

    def compose(self) -> ComposeResult:
        yield Header()

        with Static(id="top-row"):
            yield GPUPanel(id="gpu-panel")
            with Static(id="right-col"):
                yield NPUPanel(id="npu-panel")
                yield MemPanel(id="mem-panel")

        yield ProcessTable(id="process-table")
        yield CPUPanel(id="cpu-panel")
        yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(REFRESH_INTERVAL, self._tick)
        self._set_status("Ready — press ? for help")

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    async def _tick(self) -> None:
        if self._paused:
            return

        loop = asyncio.get_event_loop()
        gpu_stats, hw_stats, npu_stats, proc_stats = await asyncio.gather(
            loop.run_in_executor(None, self._pdh.collect),
            loop.run_in_executor(None, self._hw.collect),
            loop.run_in_executor(None, self._npu.collect),
            loop.run_in_executor(None, self._proc.collect),
        )

        self._last_gpu = gpu_stats
        self._last_hw = hw_stats
        self._last_npu = npu_stats

        # Push to widgets
        gpu_panel = self.query_one("#gpu-panel", GPUPanel)
        gpu_panel.hw_stats = hw_stats
        gpu_panel.gpu_stats = gpu_stats

        self.query_one("#npu-panel", NPUPanel).npu_stats = npu_stats
        self.query_one("#mem-panel", MemPanel).hw_stats = hw_stats
        self.query_one("#process-table", ProcessTable).processes = proc_stats
        self.query_one("#cpu-panel", CPUPanel).hw_stats = hw_stats

        # CSV logging
        if self._csv.active:
            self._csv.log(gpu_stats, hw_stats, npu_stats)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_toggle_pause(self) -> None:
        self._paused = not self._paused
        if self._paused:
            self.sub_title = "PAUSED — press p to resume"
            self._set_status("Paused")
        else:
            self.sub_title = "Windows 11  |  128 GB UMA"
            self._set_status("Resumed")

    def action_reset_history(self) -> None:
        from collections import deque
        panel = self.query_one("#gpu-panel", GPUPanel)
        panel._history = deque([0.0] * 60, maxlen=60)
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
            self.sub_title = "Windows 11  |  128 GB UMA"
        self._set_status(msg)

    def _set_status(self, msg: str) -> None:
        self.query_one("#status-bar", Static).update(msg)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def on_unmount(self) -> None:
        self._pdh.close()
        self._proc.close()
        if self._csv.active:
            self._csv.stop()


if __name__ == "__main__":
    GPUMonitorApp().run()
