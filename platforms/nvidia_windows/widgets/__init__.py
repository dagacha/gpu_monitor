"""NVIDIA Windows platform widgets."""
from __future__ import annotations

from platforms.nvidia_windows.widgets.cpu_panel import CPUPanel
from platforms.nvidia_windows.widgets.gpu_panel import GPUPanel
from platforms.nvidia_windows.widgets.mem_panel import MemPanel
from platforms.nvidia_windows.widgets.process_table import ProcessTable

__all__ = ["CPUPanel", "GPUPanel", "MemPanel", "ProcessTable"]
