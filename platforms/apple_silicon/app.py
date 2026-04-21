"""
gpu_monitor — htop-like GPU/CPU monitor for Apple Silicon on macOS.

Uses psutil, sysctl, vm_stat (no sudo) and powermetrics (requires sudo for GPU/power/thermal).

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
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Static

from common.config import MonitorConfig
from common.logger import CSVLogger
from common.types import SystemSnapshot
from platforms.apple_silicon.collectors import AppleSiliconCollectors
from platforms.apple_silicon.config import AppleConfig
from platforms.apple_silicon.widgets import (
    CPUPanel,
    GPUPanel,
    MemPanel,
    PowerPanel,
    ProcessMemoryTable,
    ProcessTable,
)


class AppleSiliconMonitorApp(App):
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
    #processes-row {
        layout: horizontal;
        height: auto;
    }
    #processes-row ProcessTable {
        width: 1fr;
    }
    #processes-row ProcessMemoryTable {
        width: 1fr;
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
        Binding("v", "toggle_processes", "CPU Procs"),
        Binding("m", "toggle_memory_processes", "RAM Procs"),
        Binding("c", "toggle_cpu", "CPU Panel"),
        Binding("l", "toggle_logging", "Log CSV"),
    ]

    TITLE = "GPU Monitor — Apple Silicon"
    SUB_TITLE = "macOS  |  Unified Memory Architecture"

    def __init__(self, config: AppleConfig | None = None) -> None:
        super().__init__()

        self.config = config or AppleConfig()
        self._collectors = AppleSiliconCollectors(self.config)
        self._csv = CSVLogger(log_dir=self.config.log_dir)

        self._paused = False
        self._show_processes = True
        self._show_memory_processes = True
        self._show_cpu = True

        # Cache for logging
        self._last_snapshot: SystemSnapshot | None = None

    def compose(self) -> ComposeResult:
        yield Header()

        with Static(id="top-row"):
            yield GPUPanel(id="gpu-panel")
            with Static(id="right-col"):
                yield PowerPanel(id="power-panel")
                yield MemPanel(id="mem-panel")

        with Static(id="processes-row"):
            yield ProcessTable(id="process-table")
            yield ProcessMemoryTable(id="process-memory-table")
        yield CPUPanel(id="cpu-panel")
        yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(self.config.refresh_interval, self._tick)

        # Show sudo hint if needed
        hint = self._collectors.get_sudo_hint()
        if hint:
            self._set_status(f"[dim]{hint}[/]")
        else:
            self._set_status("Ready — press ? for help")

    async def _tick(self) -> None:
        if self._paused:
            return

        loop = asyncio.get_event_loop()
        snapshot = await loop.run_in_executor(None, self._collectors.collect)

        self._last_snapshot = snapshot

        # Push to widgets
        self.query_one("#gpu-panel", GPUPanel).gpu_stats = snapshot.gpu
        self.query_one("#mem-panel", MemPanel).mem_stats = snapshot.memory
        self.query_one("#power-panel", PowerPanel).power_stats = snapshot.power
        self.query_one("#cpu-panel", CPUPanel).cpu_stats = snapshot.cpu
        self.query_one("#process-table", ProcessTable).process_stats = snapshot.processes
        self.query_one("#process-memory-table", ProcessMemoryTable).process_stats = snapshot.processes_by_memory

        # CSV logging
        if self._csv.active:
            self._csv.log(snapshot)

    def action_toggle_pause(self) -> None:
        self._paused = not self._paused
        if self._paused:
            self.sub_title = "PAUSED — press p to resume"
            self._set_status("Paused")
        else:
            self.sub_title = "macOS  |  Unified Memory Architecture"
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
            "CPU process table shown" if self._show_processes else "CPU process table hidden"
        )

    def action_toggle_memory_processes(self) -> None:
        self._show_memory_processes = not self._show_memory_processes
        pmt = self.query_one("#process-memory-table", ProcessMemoryTable)
        pmt.display = self._show_memory_processes
        self._set_status(
            "RAM process table shown" if self._show_memory_processes else "RAM process table hidden"
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
            self.sub_title = "macOS  |  Unified Memory Architecture"
        self._set_status(msg)

    def _set_status(self, msg: str) -> None:
        self.query_one("#status-bar", Static).update(msg)

    def on_unmount(self) -> None:
        if self._csv.active:
            self._csv.stop()


if __name__ == "__main__":
    AppleSiliconMonitorApp().run()
