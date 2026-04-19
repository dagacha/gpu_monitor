"""
GPU metrics for Apple Silicon via powermetrics (requires sudo).

Parses powermetrics plist output to get GPU utilization, frequency, and power.
"""
from __future__ import annotations

from common.types import GPUStats


class GPUCollector:
    """Collects GPU metrics for Apple Silicon via powermetrics.
    
    Requires sudo access to powermetrics.
    Without sudo, returns unavailable GPUStats.
    """

    def __init__(self) -> None:
        pass

    def collect(self, pm_data: dict | None) -> GPUStats:
        """Extract GPU stats from powermetrics data.
        
        Args:
            pm_data: Parsed powermetrics plist data (or None if no sudo)
        
        Returns:
            GPUStats with available=True if powermetrics has GPU data
        """
        if not pm_data or "gpu" not in pm_data:
            return GPUStats(
                available=False,
                error="GPU data requires sudo powermetrics",
            )
        
        try:
            gpu = pm_data["gpu"]
            
            # GPU active percentage (1 - idle_ratio)
            idle_ratio = gpu.get("idle_ratio", 1.0)
            active_pct = (1.0 - idle_ratio) * 100.0
            
            # GPU frequency
            freq_hz = gpu.get("freq_hz", 0)
            
            # GPU power (from processor section usually)
            gpu_power = None
            if "processor" in pm_data and "gpu_energy" in pm_data["processor"]:
                gpu_power = pm_data["processor"]["gpu_energy"] / 1000.0
            
            return GPUStats(
                total_utilization=active_pct,
                clock_mhz=freq_hz / 1e6 if freq_hz > 0 else None,
                power_w=gpu_power,
                available=True,
            )
            
        except Exception as e:
            return GPUStats(
                available=False,
                error=f"Failed to parse GPU data: {e}",
            )

    def collect_basic(self) -> GPUStats:
        """Return basic GPU stats without powermetrics.
        
        Used when no sudo is available.
        """
        return GPUStats(
            available=False,
            error="GPU data requires sudo powermetrics --samplers gpu_power",
        )
