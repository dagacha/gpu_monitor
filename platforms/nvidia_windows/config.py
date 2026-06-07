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

    # Platform identifier
    platform_name: str = "nvidia_windows"
