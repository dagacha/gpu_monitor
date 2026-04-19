"""
Power Panel — shows CPU/GPU power and thermal pressure.
Uses shared common.types and widgets.util.
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
    PowerPanel #thermal-critical {
        color: $error;
    }
    PowerPanel #thermal-heavy {
        color: $warning;
    }
    PowerPanel #thermal-moderate {
        color: $text-warning;
    }
    """

    power_stats: reactive[PowerStats | None] = reactive(None)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = "Power & Thermal"

    def compose(self) -> ComposeResult:
        yield Static("", id="power-row")
        yield Static("", id="thermal-row")

    def on_mount(self) -> None:
        self._update()

    def watch_power_stats(self, _: PowerStats | None) -> None:
        self._update()

    def _update(self) -> None:
        power = self.power_stats
        if power is None:
            return

        # Power row
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

        # Thermal row
        thermal = power.thermal_pressure or "Unknown"
        thermal_text = f"Thermal: {thermal}"
        
        thermal_widget = self.query_one("#thermal-row", Static)
        if thermal in ["Critical", "Serious"]:
            thermal_widget.id = "thermal-critical"
        elif thermal == "Fair":
            thermal_widget.id = "thermal-heavy"
        elif thermal == "Moderate":
            thermal_widget.id = "thermal-moderate"
        else:
            thermal_widget.id = "thermal-row"
        
        thermal_widget.update(thermal_text)
