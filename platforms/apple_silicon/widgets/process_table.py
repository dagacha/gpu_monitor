"""
Process Table for Apple Silicon.
Placeholder — per-process GPU tracking not implemented for macOS.
Shows top CPU processes instead.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from common.types import ProcessStats


class ProcessTable(Widget):
    DEFAULT_CSS = """
    ProcessTable {
        border: solid $accent;
        border-title-color: $accent;
        padding: 0 1;
        height: auto;
    }
    ProcessTable #pt-header {
        height: 1;
        color: $text-muted;
    }
    ProcessTable .pt-row {
        height: 1;
    }
    """

    process_stats: reactive[ProcessStats | None] = reactive(None)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "Top Processes (CPU)"

    def compose(self) -> ComposeResult:
        yield Static("Process tracking not yet implemented for macOS", id="pt-header")
        yield Static("Use Activity Monitor for per-process GPU/CPU details", classes="pt-row")

    def watch_process_stats(self, stats: ProcessStats | None) -> None:
        # Placeholder — could be extended to show top CPU processes via psutil
        pass
