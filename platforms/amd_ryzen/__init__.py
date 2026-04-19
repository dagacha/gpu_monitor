"""AMD Ryzen platform plugin for gpu_monitor.

Supports AMD Ryzen AI Max APUs on Windows 11.
Uses Windows PDH API, LibreHardwareMonitor DLL, and xrt-smi.
"""
from __future__ import annotations

import os
import sys

# Ensure common is importable
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from platforms.amd_ryzen.collectors import collect_all
from platforms.amd_ryzen.app import AMDRyzenMonitorApp

__all__ = ["collect_all", "AMDRyzenMonitorApp"]
