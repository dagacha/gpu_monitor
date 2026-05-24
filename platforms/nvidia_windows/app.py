"""
gpu_monitor — htop-like GPU/CPU monitor for NVIDIA GPUs on Windows 11.

Uses NVML (pynvml) when available, falls back to nvidia-smi. CPU sensors come
from LibreHardwareMonitor; per-core load from psutil.

Keyboard shortcuts:
    q / Ctrl+C   Quit
    p            Pause / resume
    r            Reset sparkline history
    v            Toggle process table
    c            Toggle CPU panel
    l            Toggle CSV logging
"""
from __future__ import annotations

import asyncio
import os
import subprocess
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Static

from common.logger import CSVLogger
from common.types import SystemSnapshot

from platforms.nvidia_windows.collectors import NvidiaWindowsCollectors
from platforms.nvidia_windows.config import NvidiaWindowsConfig
from platforms.nvidia_windows.widgets import CPUPanel, GPUPanel, MemPanel, ProcessTable


def _ensure_lhm(cfg: NvidiaWindowsConfig) -> None:
    """Launch LibreHardwareMonitor in the background if it is not already running."""
    try:
        import psutil
        for proc in psutil.process_iter(["name"]):
            if proc.info["name"] == "LibreHardwareMonitor.exe":
                return
    except Exception:
        pass
    if os.path.isfile(cfg.LHM_EXE):
        try:
            subprocess.Popen(
                [cfg.LHM_EXE],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception:
            pass


class NvidiaWindowsMonitorApp(App):
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

    TITLE = "GPU Monitor — NVIDIA Windows"
    SUB_TITLE = "Windows 11  |  NVML / nvidia-smi"

    def __init__(self, config: NvidiaWindowsConfig | None = None) -> None:
        super().__init__()
        self.config = config or NvidiaWindowsConfig()
        _ensure_lhm(self.config)

        self._collectors = NvidiaWindowsCollectors(self.config)
        self._csv = CSVLogger(log_dir=self.config.log_dir)

        self._paused = False
        self._show_processes = True
        self._show_cpu = True

        self._last_snapshot: SystemSnapshot | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Static(id="top-row"):
            yield GPUPanel(gpu_name=self._collectors._gpu.gpu_name, id="gpu-panel")
            with Static(id="right-col"):
                yield MemPanel(id="mem-panel")

        yield ProcessTable(id="process-table")
        yield CPUPanel(id="cpu-panel")
        yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(self.config.refresh_interval, self._tick)
        self._set_status("Ready — press q to quit")

    async def _tick(self) -> None:
        if self._paused:
            return

        loop = asyncio.get_event_loop()
        snapshot = await loop.run_in_executor(None, self._collectors.collect)

        self._last_snapshot = snapshot

        self.query_one("#gpu-panel", GPUPanel).gpu_stats = snapshot.gpu
        self.query_one("#mem-panel", MemPanel).mem_stats = snapshot.memory
        self.query_one("#process-table", ProcessTable).process_stats = snapshot.processes
        self.query_one("#cpu-panel", CPUPanel).cpu_stats = snapshot.cpu

        if self._csv.active:
            self._csv.log(snapshot)

    def action_toggle_pause(self) -> None:
        self._paused = not self._paused
        if self._paused:
            self.sub_title = "PAUSED"
            self._set_status("Paused — press p to resume")
        else:
            self.sub_title = "Windows 11  |  NVML / nvidia-smi"
            self._set_status("Resumed")

    def action_reset_history(self) -> None:
        self.query_one("#gpu-panel", GPUPanel).reset_history()
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
            self.sub_title = "Windows 11  |  NVML / nvidia-smi"
        self._set_status(msg)

    def _set_status(self, msg: str) -> None:
        self.query_one("#status-bar", Static).update(msg)

    def on_unmount(self) -> None:
        self._collectors.close()
        if self._csv.active:
            self._csv.stop()


if __name__ == "__main__":
    NvidiaWindowsMonitorApp().run()
