"""AMD Ryzen platform-specific configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass

from common.config import MonitorConfig


@dataclass
class AMDConfig(MonitorConfig):
    """Configuration for AMD Ryzen platform."""

    # LibreHardwareMonitor path
    LHM_PATH: str = os.environ.get(
        "GPU_MONITOR_LHM_PATH",
        r"C:\Users\Office\LibreHardwareMonitor",
    )
    LHM_EXE: str = os.environ.get(
        "GPU_MONITOR_LHM_EXE",
        os.path.join(LHM_PATH, "LibreHardwareMonitor.exe"),
    )

    # AMD XRT-SMI tool
    XRT_SMI: str = os.environ.get(
        "GPU_MONITOR_XRT_SMI",
        r"C:\Windows\System32\AMD\xrt-smi.exe",
    )

    # Platform identifier
    platform_name: str = "amd_ryzen"

    def __post_init__(self):
        super().__post_init__()
        # Ensure LHM_EXE is properly set based on LHM_PATH if not explicitly set
        if not os.environ.get("GPU_MONITOR_LHM_EXE"):
            self.LHM_EXE = os.path.join(self.LHM_PATH, "LibreHardwareMonitor.exe")
