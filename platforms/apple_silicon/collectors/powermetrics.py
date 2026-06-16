"""
powermetrics runner for Apple Silicon.

Handles running powermetrics with sudo and parsing plist output.
"""
from __future__ import annotations

import plistlib
import subprocess
import threading
from typing import Optional

from common.debug import get_logger
from platforms.apple_silicon.config import AppleConfig

_log = get_logger("apple.powermetrics")


def energy_to_watts(section: dict, base: str, interval_ms: int) -> float | None:
    """Convert a powermetrics power/energy field to watts.

    powermetrics reports either an instantaneous ``<base>_power`` in mW or
    a ``<base>_energy`` accumulated over the sample interval in mJ. Average
    power in watts from energy is ``mJ / interval_ms`` (since mJ/ms == W),
    not ``mJ / 1000`` — the latter is only correct at a 1000 ms interval.
    """
    if not isinstance(section, dict) or interval_ms <= 0:
        return None
    power_key = f"{base}_power"
    if power_key in section:
        try:
            return float(section[power_key]) / 1000.0  # mW -> W
        except (TypeError, ValueError):
            return None
    energy_key = f"{base}_energy"
    if energy_key in section:
        try:
            return float(section[energy_key]) / interval_ms  # mJ / ms == W
        except (TypeError, ValueError):
            return None
    return None


class PowerMetricsRunner:
    """Runs powermetrics and parses output.
    
    This spawns a subprocess with sudo for each sample.
    The sample interval is controlled by powermetrics -i flag.
    """

    def __init__(self, config: AppleConfig | None = None) -> None:
        self.config = config or AppleConfig()
        self._available: bool | None = None
        # A powermetrics sample takes ~1s, which can exceed the refresh
        # interval. Serialize samples so overlapping ticks don't spawn a
        # pile of concurrent `sudo powermetrics` processes; a tick that
        # arrives mid-sample reuses the most recent result instead.
        self._sample_lock = threading.Lock()
        self._last_sample: dict | None = None

    def is_available(self) -> bool:
        """Check if powermetrics is available (binary exists)."""
        if self._available is None:
            import os
            self._available = os.path.isfile(self.config.POWERMETRICS_PATH)
        return self._available

    def can_run_with_sudo(self) -> bool:
        """Check if we can run powermetrics with sudo non-interactively."""
        return self.config.has_sudo_access

    def sample(self) -> dict | None:
        """Take a single sample from powermetrics.
        
        Returns:
            Parsed plist dict, or None if not available/no sudo.
        """
        if not self.is_available():
            return None
        
        if not self.can_run_with_sudo():
            return None

        # If a sample is already running, reuse the most recent result
        # rather than queueing another `sudo powermetrics` subprocess.
        if not self._sample_lock.acquire(blocking=False):
            return self._last_sample

        try:
            sample = self._run_sample()
            if sample is not None:
                self._last_sample = sample
            return sample
        finally:
            self._sample_lock.release()

    def _run_sample(self) -> dict | None:
        try:
            # Run powermetrics for one sample with plist output
            cmd = [
                "sudo", "-n",  # Non-interactive sudo
                self.config.POWERMETRICS_PATH,
                "-i", str(self.config.powermetrics_interval_ms),
                "-n", "1",  # One sample
                "--samplers", self.config.powermetrics_samplers,
                "-f", "plist",
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=(self.config.powermetrics_interval_ms / 1000) + 5,
            )
            
            if result.returncode != 0:
                # Check if it's a sudo issue
                stderr = result.stderr.decode().lower()
                if "password" in stderr or "sudo" in stderr:
                    self.config._has_sudo = False
                _log.debug("powermetrics exited %s: %s", result.returncode, stderr.strip())
                return None
            
            # Parse plist output
            # powermetrics outputs binary plist with some header text
            # Find the plist start
            data = result.stdout
            
            # Try to find plist magic bytes (bplist00)
            if b"bplist00" in data:
                plist_start = data.find(b"bplist00")
                plist_data = data[plist_start:]
                return plistlib.loads(plist_data)
            
            # Fallback: try to parse as XML plist
            try:
                return plistlib.loads(data)
            except Exception:
                _log.debug("failed to parse powermetrics plist output", exc_info=True)
            
            return None
            
        except subprocess.TimeoutExpired:
            _log.debug("powermetrics sample timed out", exc_info=True)
            return None
        except Exception:
            _log.debug("powermetrics sample failed", exc_info=True)
            return None

    def sample_once(self) -> dict | None:
        """Convenience alias for sample()."""
        return self.sample()
