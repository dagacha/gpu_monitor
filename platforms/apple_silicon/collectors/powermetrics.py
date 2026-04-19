"""
powermetrics runner for Apple Silicon.

Handles running powermetrics with sudo and parsing plist output.
"""
from __future__ import annotations

import plistlib
import subprocess
from typing import Optional

from platforms.apple_silicon.config import AppleConfig


class PowerMetricsRunner:
    """Runs powermetrics and parses output.
    
    This spawns a subprocess with sudo for each sample.
    The sample interval is controlled by powermetrics -i flag.
    """

    def __init__(self, config: AppleConfig | None = None) -> None:
        self.config = config or AppleConfig()
        self._available: bool | None = None

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
                pass
            
            return None
            
        except subprocess.TimeoutExpired:
            return None
        except Exception:
            return None

    def sample_once(self) -> dict | None:
        """Convenience alias for sample()."""
        return self.sample()
