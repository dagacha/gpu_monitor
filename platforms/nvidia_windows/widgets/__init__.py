"""NVIDIA Windows platform widgets.

Re-exports the NVIDIA Linux widgets — they're pure UI bound to shared types and
work identically on Windows. Split into their own modules later if the Windows
variant needs to diverge.
"""
from __future__ import annotations

from platforms.nvidia_linux.widgets.cpu_panel import CPUPanel
from platforms.nvidia_linux.widgets.gpu_panel import GPUPanel
from platforms.nvidia_linux.widgets.mem_panel import MemPanel
from platforms.nvidia_linux.widgets.process_table import ProcessTable

__all__ = ["CPUPanel", "GPUPanel", "MemPanel", "ProcessTable"]
