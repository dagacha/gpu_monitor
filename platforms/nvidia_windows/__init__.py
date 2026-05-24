"""NVIDIA Windows platform plugin for gpu_monitor.

Supports NVIDIA GPUs on Windows 11 via NVML (primary) or nvidia-smi (fallback),
with CPU sensors from LibreHardwareMonitor.
"""
from __future__ import annotations

import os
import sys

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from platforms.nvidia_windows.collectors import NvidiaWindowsCollectors

__all__ = ["NvidiaWindowsCollectors", "NvidiaWindowsMonitorApp"]


def __getattr__(name: str):
    """Lazy-load the Textual app so `python -m platforms.nvidia_windows.app`
    doesn't double-import (RuntimeWarning about sys.modules)."""
    if name == "NvidiaWindowsMonitorApp":
        from platforms.nvidia_windows.app import NvidiaWindowsMonitorApp
        return NvidiaWindowsMonitorApp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
