"""AMD Ryzen platform widgets."""
from __future__ import annotations

from platforms.amd_ryzen.widgets.cpu_panel import CPUPanel
from platforms.amd_ryzen.widgets.gpu_panel import GPUPanel
from platforms.amd_ryzen.widgets.mem_panel import MemPanel
from platforms.amd_ryzen.widgets.npu_panel import NPUPanel
from platforms.amd_ryzen.widgets.power_panel import PowerPanel
from platforms.amd_ryzen.widgets.process_table import ProcessTable

__all__ = [
    "CPUPanel",
    "GPUPanel",
    "MemPanel",
    "NPUPanel",
    "PowerPanel",
    "ProcessTable",
]
