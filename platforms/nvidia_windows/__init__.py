"""NVIDIA Windows platform plugin for gpu_monitor.

Supports NVIDIA GPUs on Windows via nvidia-smi and psutil.
"""
from __future__ import annotations

import os
import sys

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from platforms.nvidia_windows.collectors import NvidiaWindowsCollectors
from platforms.nvidia_windows.app import NvidiaWindowsMonitorApp

__all__ = ["NvidiaWindowsCollectors", "NvidiaWindowsMonitorApp"]
