"""
GPU metrics for Apple Silicon via powermetrics (requires sudo).

Parses powermetrics plist output to get GPU utilization, frequency, and power.
"""
from __future__ import annotations

from common.debug import get_logger
from common.types import GPUStats
from platforms.apple_silicon.collectors.powermetrics import energy_to_watts

_log = get_logger("apple.gpu")


class GPUCollector:
    """Collects GPU metrics for Apple Silicon via powermetrics.
    
    Requires sudo access to powermetrics.
    Without sudo, returns unavailable GPUStats.
    """

    def __init__(self) -> None:
        pass

    def collect(self, pm_data: dict | None, interval_ms: int = 1000) -> GPUStats:
        """Extract GPU stats from powermetrics data.
        
        Args:
            pm_data: Parsed powermetrics plist data (or None if no sudo)
            interval_ms: powermetrics sample interval, used to convert
                accumulated energy (mJ) into average power (W).
        
        Returns:
            GPUStats with available=True if powermetrics has GPU data
        """
        if not pm_data or "gpu" not in pm_data:
            return GPUStats(
                total_utilization=0.0,
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
            gpu_power = energy_to_watts(pm_data.get("processor", {}), "gpu", interval_ms)
            
            return GPUStats(
                total_utilization=active_pct,
                clock_mhz=freq_hz / 1e6 if freq_hz > 0 else None,
                power_w=gpu_power,
                available=True,
            )
            
        except Exception as e:
            _log.debug("failed to parse GPU data", exc_info=True)
            return GPUStats(
                total_utilization=0.0,
                available=False,
                error=f"Failed to parse GPU data: {e}",
            )

    def collect_basic(self) -> GPUStats:
        """Return basic GPU stats without powermetrics.
        
        Used when no sudo is available.
        """
        return GPUStats(
            total_utilization=0.0,
            available=False,
            error="GPU data requires sudo powermetrics --samplers gpu_power",
        )
