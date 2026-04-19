"""Configuration module for gpu_monitor.

All paths can be overridden via environment variables:
    GPU_MONITOR_LHM_PATH      - Path to LibreHardwareMonitor directory
    GPU_MONITOR_XRT_SMI       - Path to xrt-smi executable
"""
from __future__ import annotations

import os

# LibreHardwareMonitor path
LHM_PATH = os.environ.get(
    "GPU_MONITOR_LHM_PATH",
    r"C:\Users\Office\LibreHardwareMonitor",
)
LHM_EXE = os.path.join(LHM_PATH, "LibreHardwareMonitor.exe")

# AMD XRT-SMI tool path
XRT_SMI = os.environ.get(
    "GPU_MONITOR_XRT_SMI",
    r"C:\Windows\System32\AMD\xrt-smi.exe",
)
