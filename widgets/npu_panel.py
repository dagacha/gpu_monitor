"""
NPU Panel — AMD XDNA / AIE status via xrt-smi.
Shows partitions, active HW contexts, GOPS, driver/firmware versions.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from collectors.npu import NPUStats

_MAX_PARTITIONS = 6


class NPUPanel(Widget):
    DEFAULT_CSS = """
    NPUPanel {
        border: solid $accent;
        border-title-color: $accent;
        padding: 0 1;
        height: auto;
    }
    NPUPanel Static { height: 1; }
    NPUPanel #npu-versions { color: $text-muted; }
    """

    npu_stats: reactive[NPUStats | None] = reactive(None)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "NPU  (AMD XDNA / AIE)"

    def compose(self) -> ComposeResult:
        yield Static("Status:  --", id="npu-status")
        yield Static("", id="npu-summary")
        yield Static("", id="npu-gops")
        for i in range(_MAX_PARTITIONS):
            yield Static("", id=f"npu-part-{i}")
        yield Static("", id="npu-versions")

    def watch_npu_stats(self, stats: NPUStats | None) -> None:
        if stats is None:
            return

        status  = self.query_one("#npu-status",  Static)
        summary = self.query_one("#npu-summary", Static)
        gops_w  = self.query_one("#npu-gops",    Static)
        vers    = self.query_one("#npu-versions", Static)

        if not stats.available:
            status.update(f"[red]{stats.error}[/]")
            summary.update("")
            gops_w.update("")
            vers.update("")
            for i in range(_MAX_PARTITIONS):
                self.query_one(f"#npu-part-{i}", Static).update("")
            return

        status.update("Status:  [green]online[/]")

        summary.update(
            f"Partitions: {len(stats.partitions)}  |  "
            f"Contexts: {stats.total_contexts}  |  "
            f"Active: {stats.active_contexts}"
        )

        total_g = stats.total_gops
        total_eg = stats.total_egops
        if total_g > 0 or total_eg > 0:
            gops_w.update(f"GOPS: {total_g:.0f}  |  Effective GOPS: {total_eg:.0f}")
        else:
            gops_w.update("GOPS: idle")

        # Per-partition rows
        for i in range(_MAX_PARTITIONS):
            row = self.query_one(f"#npu-part-{i}", Static)
            if i < len(stats.partitions):
                p = stats.partitions[i]
                cols = f"cols[{','.join(str(c) for c in p.columns)}]"
                ctx_str = f"{len(p.contexts)} ctx"
                gops_str = f"{p.total_gops:.0f} GOPS" if p.total_gops > 0 else "idle"
                row.update(f"  [dim]Part {p.index}[/] {cols}  {ctx_str}  {gops_str}")
            else:
                row.update("")

        # Versions (bottom)
        parts = []
        if stats.xrt_version:
            parts.append(f"XRT {stats.xrt_version}")
        if stats.firmware_version:
            parts.append(f"FW {stats.firmware_version}")
        vers.update("  |  ".join(parts))
