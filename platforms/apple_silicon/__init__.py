"""Apple Silicon platform plugin for gpu_monitor.

Supports Apple Silicon Macs (M1/M2/M3/M4 series) on macOS.
Uses psutil, sysctl, vm_stat, and powermetrics (sudo required for GPU/power/thermal).
"""
from __future__ import annotations

import os
import sys

# Ensure common is importable
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from platforms.apple_silicon.collectors import AppleSiliconCollectors
from platforms.apple_silicon.app import AppleSiliconMonitorApp

__all__ = ["AppleSiliconCollectors", "AppleSiliconMonitorApp"]
