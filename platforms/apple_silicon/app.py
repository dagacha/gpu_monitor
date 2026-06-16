"""
gpu_monitor — htop-like GPU/CPU monitor for Apple Silicon on macOS.

Uses psutil, sysctl, vm_stat (no sudo) and powermetrics (requires sudo for GPU/power/thermal).

Keyboard shortcuts:
    q / Ctrl+C   Quit
    p            Pause / resume
    r            Reset sparkline history
    v            Toggle CPU process table
    m            Toggle RAM process table
    c            Toggle CPU panel
    l            Toggle CSV logging
"""
from __future__ import annotations

from typing import ClassVar

from textual.binding import Binding
from textual.widgets import Footer, Header, Static

from common.base_app import BaseMonitorApp
from common.config import MonitorConfig

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


class AppleSiliconMonitorApp(BaseMonitorApp):
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
        *BaseMonitorApp.BASE_BINDINGS,
        Binding("m", "toggle_memory_processes", "RAM Procs"),
    ]

    TITLE = "GPU Monitor — Apple Silicon"
    SUB_TITLE = "macOS  |  Unified Memory Architecture"

    def __init__(self, config: MonitorConfig | None = None) -> None:
        super().__init__(config or AppleConfig())
        self._collectors = AppleSiliconCollectors(self.config)
        self._show_memory_processes = True

    def compose(self):
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
        """Start the tick timer, then show a sudo hint if powermetrics needs it."""
        super().on_mount()
        try:
            hint = self._collectors.get_sudo_hint()
        except Exception:
            hint = None
        if hint:
            self._set_status(f"[dim]{hint}[/]")

    def action_toggle_processes(self) -> None:
        self._show_processes = not self._show_processes
        try:
            pt = self.query_one("#process-table")
            pt.display = self._show_processes
        except Exception:
            return
        self._set_status(
            "CPU process table shown" if self._show_processes else "CPU process table hidden"
        )

    def action_toggle_memory_processes(self) -> None:
        self._show_memory_processes = not self._show_memory_processes
        try:
            pmt = self.query_one("#process-memory-table")
            pmt.display = self._show_memory_processes
        except Exception:
            return
        self._set_status(
            "RAM process table shown"
            if self._show_memory_processes
            else "RAM process table hidden"
        )


if __name__ == "__main__":
    AppleSiliconMonitorApp().run()
