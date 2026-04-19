"""
Power and thermal metrics for Apple Silicon via powermetrics (requires sudo).

Also provides a fallback to memory_pressure for thermal info without sudo.
"""
from __future__ import annotations

import subprocess
from typing import Optional

from common.types import PowerStats


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
        pass
    return None


class PowerCollector:
    """Collects power and thermal metrics for Apple Silicon.
    
    Primary source: powermetrics (requires sudo)
    Fallback: memory_pressure for thermal (no sudo)
    """

    def __init__(self) -> None:
        pass

    def collect(self, pm_data: dict | None) -> PowerStats:
        """Extract power/thermal from powermetrics data.
        
        Args:
            pm_data: Parsed powermetrics plist data (or None if no sudo)
        
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
                if "processor" in pm_data:
                    proc = pm_data["processor"]
                    
                    # CPU power (cpu_energy is in mJ)
                    if "cpu_energy" in proc:
                        cpu_power = proc["cpu_energy"] / 1000.0
                    
                    # GPU power
                    if "gpu_energy" in proc:
                        gpu_power = proc["gpu_energy"] / 1000.0
                    
                    # Package power (combined)
                    if "combined_power" in proc:
                        package_power = proc["combined_power"] / 1000.0
                    elif cpu_power or gpu_power:
                        package_power = (cpu_power or 0.0) + (gpu_power or 0.0)
                
                # Thermal pressure
                if "thermal_pressure" in pm_data:
                    thermal = pm_data["thermal_pressure"]
                
            except Exception:
                pass
        
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
