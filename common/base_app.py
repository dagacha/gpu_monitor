"""Base Textual App class shared by all gpu_monitor platforms.

Each platform-specific app (NVIDIA Windows/Linux, AMD Ryzen, Apple
Silicon) inherits from `BaseMonitorApp` to get:

- A shared set of keyboard bindings (`q` quit, `p` pause, `r` reset,
  `v` toggle process table, `c` toggle CPU panel, `l` toggle CSV log).
- Standard actions (`action_toggle_pause`, `action_toggle_logging`,
  `action_reset_history`, `action_toggle_processes`, `action_toggle_cpu`).
- A safe `_set_status` helper for the `#status-bar` Static widget.
- An `_tick()` loop that runs `self._collectors.collect()` in an
  executor so the Textual event loop stays responsive.
- A widget-pushing convention that pushes `SystemSnapshot` fields to
  widgets by ID, skipping any widget IDs the platform did not compose.
- CSV-logger lifecycle (`on_unmount` stops an open logger).

Subclass contract
-----------------

Subclasses are expected to:

- Set class attributes `TITLE` and `SUB_TITLE`.
- Optionally append bindings via ``BINDINGS = [*BASE_BINDINGS, ...]``.
- Implement ``compose()`` to lay out platform-specific widgets.
- Set ``self._collectors`` (a sync object with ``.collect() -> SystemSnapshot``
  or ``.collect() -> tuple[SystemSnapshot, extra]``) before the timer fires.
- Override ``on_mount()`` if they need extra init — always call
  ``super().on_mount()`` to start the tick timer.
- Override ``_update_extra_widgets(snapshot, extra)`` if they need to push
  to widgets the base doesn't know about (e.g. AMD's NPU panel).
"""
from __future__ import annotations

import asyncio
import os
from typing import Any, ClassVar

from textual.app import App
from textual.binding import Binding
from textual.widgets import Static

from common.config import MonitorConfig
from common.logger import CSVLogger
from common.types import SystemSnapshot


class BaseMonitorApp(App):
    """Shared scaffolding for every gpu_monitor Textual app."""

    BASE_BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "Quit"),
        Binding("p", "toggle_pause", "Pause"),
        Binding("r", "reset_history", "Reset"),
        Binding("v", "toggle_processes", "Processes"),
        Binding("c", "toggle_cpu", "CPU Panel"),
        Binding("l", "toggle_logging", "Log CSV"),
    ]

    # Subclasses typically override BINDINGS and SUB_TITLE.
    BINDINGS: ClassVar[list[Binding]] = BASE_BINDINGS
    SUB_TITLE: ClassVar[str] = ""

    def __init__(self, config: MonitorConfig | None = None) -> None:
        super().__init__()
        self.config = config or self.default_config()
        self._csv = CSVLogger(log_dir=self.config.log_dir)
        self._paused = False
        self._show_processes = True
        self._show_cpu = True
        self._last_snapshot: SystemSnapshot | None = None
        self._last_extra: Any = None
        # Subclasses typically set self._collectors after super().__init__
        # (e.g. when it needs platform-specific config to be applied first).

    @classmethod
    def default_config(cls) -> MonitorConfig:
        """Subclasses override to return their platform-specific config."""
        return MonitorConfig()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self.set_interval(self.config.refresh_interval, self._tick)
        self._set_status("Ready — press ? for help")

    def on_unmount(self) -> None:
        self._on_close()
        if self._csv.active:
            self._csv.stop()

    def _on_close(self) -> None:
        """Hook for subclasses to release platform-specific resources.

        Called from ``on_unmount()`` before the CSV logger is stopped.
        The default implementation is a no-op.
        """

    async def _tick(self) -> None:
        """Default tick loop — runs collectors and pushes snapshot to widgets."""
        if self._paused:
            return
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._collectors.collect)
        if isinstance(result, tuple):
            snapshot, extra = result
        else:
            snapshot, extra = result, None

        self._last_snapshot = snapshot
        self._last_extra = extra
        self._push_snapshot_to_widgets(snapshot, extra)

        if self._csv.active:
            self._csv.log(snapshot)

    def _push_snapshot_to_widgets(
        self, snapshot: SystemSnapshot, extra: Any = None
    ) -> None:
        """Push common snapshot fields to widgets by ID convention.

        Each (selector, attribute, value) tuple is applied only when a
        widget matching the selector has been composed by the subclass —
        this lets each platform compose only the widgets it needs.
        """
        pairs = [
            ("#gpu-panel", "gpu_stats", snapshot.gpu),
            ("#mem-panel", "mem_stats", snapshot.memory),
            ("#cpu-panel", "cpu_stats", snapshot.cpu),
            ("#process-table", "process_stats", snapshot.processes),
            ("#power-panel", "power_stats", snapshot.power),
            ("#process-memory-table", "process_stats", snapshot.processes_by_memory),
        ]
        for selector, attr, value in pairs:
            try:
                widget = self.query_one(selector)
                setattr(widget, attr, value)
            except Exception:
                # Widget not composed on this platform — skip silently.
                continue
        self._update_extra_widgets(snapshot, extra)

    def _update_extra_widgets(self, snapshot: SystemSnapshot, extra: Any) -> None:
        """Hook for subclasses to push to platform-specific widgets.

        Default is a no-op. AMD's subclass overrides this to update the
        NPU panel from `extra` (an ``NPUStats`` instance).
        """

    # ------------------------------------------------------------------
    # Standard actions
    # ------------------------------------------------------------------

    def action_toggle_pause(self) -> None:
        self._paused = not self._paused
        if self._paused:
            self._set_status("Paused — press p to resume")
            self.sub_title = "PAUSED"
        else:
            self._set_status("Resumed")
            self.sub_title = self._default_subtitle()

    def action_reset_history(self) -> None:
        try:
            panel = self.query_one("#gpu-panel")
        except Exception:
            return
        if hasattr(panel, "reset_history"):
            panel.reset_history()
            self._set_status("Sparkline history reset")

    def action_toggle_processes(self) -> None:
        self._show_processes = not self._show_processes
        try:
            pt = self.query_one("#process-table")
            pt.display = self._show_processes
        except Exception:
            return
        self._set_status(
            "Process table shown" if self._show_processes else "Process table hidden"
        )

    def action_toggle_cpu(self) -> None:
        self._show_cpu = not self._show_cpu
        try:
            cp = self.query_one("#cpu-panel")
            cp.display = self._show_cpu
        except Exception:
            return
        self._set_status(
            "CPU panel shown" if self._show_cpu else "CPU panel hidden"
        )

    def action_toggle_logging(self) -> None:
        msg = self._csv.toggle()
        if self._csv.active:
            self.sub_title = f"● REC  {os.path.basename(self._csv.path)}"
        else:
            self.sub_title = self._default_subtitle()
        self._set_status(msg)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_status(self, msg: str) -> None:
        """Update the status bar. Silent if `#status-bar` is missing."""
        try:
            self.query_one("#status-bar", Static).update(msg)
        except Exception:
            pass

    def _default_subtitle(self) -> str:
        return self.SUB_TITLE or ""
