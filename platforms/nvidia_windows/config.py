"""NVIDIA Windows platform-specific configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass

from common.config import MonitorConfig


@dataclass
class NvidiaConfig(MonitorConfig):
    """Configuration for NVIDIA Windows platform."""

    # nvidia-smi path on Windows
    NVSMI_PATH: str = os.environ.get(
        "NVSMI_PATH",
        r"C:\Windows\System32\nvidia-smi.exe",
    )

    # LibreHardwareMonitor directory (for CPU temp/power sensors).
    # Same env override as the AMD platform.
    LHM_PATH: str = os.environ.get(
        "GPU_MONITOR_LHM_PATH",
        os.path.expandvars(r"%USERPROFILE%\LibreHardwareMonitor"),
    )

    # Platform identifier
    platform_name: str = "nvidia_windows"
