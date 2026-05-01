"""NVIDIA Linux platform-specific configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass

from common.config import MonitorConfig


@dataclass
class NvidiaConfig(MonitorConfig):
    """Configuration for NVIDIA Linux platform."""

    # nvidia-smi path
    NVSMI_PATH: str = os.environ.get(
        "NVSMI_PATH",
        "/usr/bin/nvidia-smi",
    )

    # Platform identifier
    platform_name: str = "nvidia_linux"
