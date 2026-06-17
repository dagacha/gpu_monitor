"""Apple Silicon platform-specific configuration."""
from __future__ import annotations

import os
import time
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

    # How long (seconds) a sudo-availability result stays cached before
    # being re-probed. A short TTL lets the app recover if the user grants
    # sudo after launch, and notices when a cached sudo credential expires.
    sudo_cache_ttl: float = 30.0

    def __post_init__(self):
        super().__post_init__()
        # Cached sudo state + when it was last determined (monotonic clock).
        self._has_sudo: bool | None = None
        self._has_sudo_checked_at: float = 0.0

    def _probe_sudo(self) -> bool:
        """Run a cheap non-interactive sudo probe against powermetrics."""
        import subprocess
        try:
            result = subprocess.run(
                ["sudo", "-n", self.POWERMETRICS_PATH, "--help"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    @property
    def has_sudo_access(self) -> bool:
        """Whether powermetrics can run under non-interactive sudo.

        The result is cached for ``sudo_cache_ttl`` seconds and then
        re-probed, so the app recovers if the user authorizes sudo after
        launch (or loses it when a cached sudo credential expires).
        """
        now = time.monotonic()
        if (
            self._has_sudo is None
            or (now - self._has_sudo_checked_at) >= self.sudo_cache_ttl
        ):
            self._has_sudo = self._probe_sudo()
            self._has_sudo_checked_at = now
        return self._has_sudo

    def record_sudo_failure(self) -> None:
        """Mark sudo as unavailable after a non-interactive sudo attempt
        failed (e.g. powermetrics asked for a password). Keeps this config
        the single source of truth for sudo state. The TTL still applies,
        so it will be re-probed rather than latched off permanently."""
        self._has_sudo = False
        self._has_sudo_checked_at = time.monotonic()
