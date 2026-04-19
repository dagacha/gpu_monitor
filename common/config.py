"""Base configuration for gpu_monitor.

Platform-specific configs should extend this with their own paths and settings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MonitorConfig:
    """Base configuration for the GPU monitor.

    Platform-specific implementations should create instances of this
    or extend it with additional platform-specific settings.
    """
    # Refresh interval in seconds
    refresh_interval: float = 1.0

    # History length for sparkline graphs
    history_length: int = 60

    # Default bar width for progress bars
    bar_width: int = 28

    # CPU panel settings
    max_cores_display: int = 32
    cpu_bar_width: int = 18

    # CSV logging
    log_dir: Optional[str] = None
    log_filename: Optional[str] = None

    # Platform identifier
    platform_name: str = "generic"

    def __post_init__(self):
        if self.log_dir is None:
            import os
            self.log_dir = os.getcwd()
