"""
Power Panel — shows CPU/GPU/SoC power on AMD Ryzen.

Thermal pressure is a macOS-only concept and isn't shown here; per-component
temperatures live in the GPU and CPU panels.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from common.types import PowerStats
from common.widgets.util import fmt_watts


class PowerPanel(Widget):
    DEFAULT_CSS = """
    PowerPanel {
        border: solid $accent;
        border-title-color: $accent;
        padding: 0 1;
        height: auto;
    }
    PowerPanel Static {
        height: 1;
    }
    """

    power_stats: reactive[PowerStats | None] = reactive(None)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "Power"

    def compose(self) -> ComposeResult:
        yield Static("", id="power-row")

    def on_mount(self) -> None:
        self._update()

    def watch_power_stats(self, _: PowerStats | None) -> None:
        self._update()

    def _update(self) -> None:
        power = self.power_stats
        if power is None:
            return

        power_parts = []
        if power.cpu_power_w is not None:
            power_parts.append(f"CPU: {fmt_watts(power.cpu_power_w)}")
        if power.gpu_power_w is not None:
            power_parts.append(f"GPU: {fmt_watts(power.gpu_power_w)}")
        if power.soc_power_w is not None:
            power_parts.append(f"[bold]SoC: {fmt_watts(power.soc_power_w)}[/]")

        self.query_one("#power-row", Static).update(
            "  |  ".join(power_parts) if power_parts else "Power data unavailable"
        )
