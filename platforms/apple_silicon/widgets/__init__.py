"""Apple Silicon platform widgets."""
from __future__ import annotations

from platforms.apple_silicon.widgets.cpu_panel import CPUPanel
from platforms.apple_silicon.widgets.gpu_panel import GPUPanel
from platforms.apple_silicon.widgets.mem_panel import MemPanel
from platforms.apple_silicon.widgets.power_panel import PowerPanel
from platforms.apple_silicon.widgets.process_table import ProcessTable

__all__ = [
    "CPUPanel",
    "GPUPanel",
    "MemPanel",
    "PowerPanel",
    "ProcessTable",
]
