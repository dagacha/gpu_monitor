"""Apple Silicon platform-specific configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass

from common.config import MonitorConfig


@dataclass
class AppleConfig(MonitorConfig):
    """Configuration for Apple Silicon platform."""

    # powermetrics path (requires sudo)
    POWERMETRICS_PATH: str = "/usr/bin/powermetrics"

    # Sample interval for powermetrics (ms)
    powermetrics_interval_ms: int = 1000

    # Platform identifier
    platform_name: str = "apple_silicon"

    # Samplers to use with powermetrics
    powermetrics_samplers: str = "cpu_power,gpu_power,thermal"

    # Page size for vm_stat (default 16384 on Apple Silicon)
    page_size: int = 16384

    def __post_init__(self):
        super().__post_init__()
        # Check if we have sudo access by testing powermetrics
        self._has_sudo: bool | None = None

    @property
    def has_sudo_access(self) -> bool:
        """Check if we can run powermetrics with sudo."""
        if self._has_sudo is None:
            # Try to run powermetrics with -n (non-interactive) flag
            import subprocess
            try:
                result = subprocess.run(
                    ["sudo", "-n", self.POWERMETRICS_PATH, "--help"],
                    capture_output=True,
                    timeout=5,
                )
                self._has_sudo = result.returncode == 0
            except Exception:
                self._has_sudo = False
        return self._has_sudo
