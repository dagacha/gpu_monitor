"""NVIDIA Windows platform-specific configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass

from common.config import MonitorConfig


def _default_nvsmi_path() -> str:
    """Pick the first existing nvidia-smi.exe from the standard install locations."""
    candidates = [
        r"C:\Windows\System32\nvidia-smi.exe",
        r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return candidates[0]


@dataclass
class NvidiaWindowsConfig(MonitorConfig):
    """Configuration for NVIDIA Windows platform."""

    # nvidia-smi path (fallback when NVML unavailable; also used for per-process queries)
    NVSMI_PATH: str = os.environ.get("NVSMI_PATH", _default_nvsmi_path())

    # LibreHardwareMonitor (for CPU temp/clock/power)
    LHM_PATH: str = os.environ.get(
        "GPU_MONITOR_LHM_PATH",
        r"C:\Users\Office\LibreHardwareMonitor",
    )
    LHM_EXE: str = os.environ.get(
        "GPU_MONITOR_LHM_EXE",
        "",
    )

    platform_name: str = "nvidia_windows"

    def __post_init__(self):
        super().__post_init__()
        if not self.LHM_EXE:
            self.LHM_EXE = os.path.join(self.LHM_PATH, "LibreHardwareMonitor.exe")
