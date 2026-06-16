"""
Power and thermal metrics for Apple Silicon via powermetrics (requires sudo).

Also provides a fallback to memory_pressure for thermal info without sudo.
"""
from __future__ import annotations

import subprocess
from typing import Optional

from common.debug import get_logger
from common.types import PowerStats
from platforms.apple_silicon.collectors.powermetrics import energy_to_watts

_log = get_logger("apple.power")


def _memory_pressure() -> str | None:
    """Get thermal pressure from memory_pressure (no sudo required)."""
    try:
        result = subprocess.run(
            ["memory_pressure"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            # Look for "The system has X% of available memory"
            # or similar indicators
            output = result.stdout.lower()
            if "critical" in output or "swap" in output:
                return "Critical"
            elif "pressure" in output or "heavy" in output:
                return "Serious"
            elif "moderate" in output:
                return "Fair"
            else:
                return "Nominal"
    except Exception:
        _log.debug("memory_pressure failed", exc_info=True)
    return None


class PowerCollector:
    """Collects power and thermal metrics for Apple Silicon.
    
    Primary source: powermetrics (requires sudo)
    Fallback: memory_pressure for thermal (no sudo)
    """

    def __init__(self) -> None:
        pass

    def collect(self, pm_data: dict | None, interval_ms: int = 1000) -> PowerStats:
        """Extract power/thermal from powermetrics data.
        
        Args:
            pm_data: Parsed powermetrics plist data (or None if no sudo)
            interval_ms: powermetrics sample interval, used to convert
                accumulated energy (mJ) into average power (W).
        
        Returns:
            PowerStats with available data
        """
        cpu_power: float | None = None
        gpu_power: float | None = None
        package_power: float | None = None
        thermal: str | None = None
        
        # Try powermetrics data first (requires sudo)
        if pm_data:
            try:
                # Power data is in processor section
                proc = pm_data.get("processor")
                if isinstance(proc, dict):
                    cpu_power = energy_to_watts(proc, "cpu", interval_ms)
                    gpu_power = energy_to_watts(proc, "gpu", interval_ms)
                    
                    # Package power (combined)
                    package_power = energy_to_watts(proc, "combined", interval_ms)
                    if package_power is None and (cpu_power or gpu_power):
                        package_power = (cpu_power or 0.0) + (gpu_power or 0.0)
                
                # Thermal pressure
                if "thermal_pressure" in pm_data:
                    thermal = pm_data["thermal_pressure"]
                
            except Exception:
                _log.debug("failed to parse power data", exc_info=True)
        
        # Fallback for thermal without sudo
        if thermal is None:
            thermal = _memory_pressure()
        
        # Check if we have any useful data
        available = any([
            cpu_power is not None,
            gpu_power is not None,
            thermal is not None,
        ])
        
        if not available:
            return PowerStats(
                available=False,
                error="Power/thermal data requires sudo powermetrics",
            )
        
        return PowerStats(
            cpu_power_w=cpu_power,
            gpu_power_w=gpu_power,
            package_power_w=package_power,
            thermal_pressure=thermal,
            available=True,
        )

    def collect_basic(self) -> PowerStats:
        """Return basic thermal info without powermetrics."""
        thermal = _memory_pressure()
        
        if thermal:
            return PowerStats(
                thermal_pressure=thermal,
                available=True,
            )
        
        return PowerStats(
            available=False,
            error="Install psutil and run with sudo for power/thermal data",
        )
