"""
CPU metrics for Apple Silicon via psutil and sysctl.
No sudo required for basic CPU data.
"""
from __future__ import annotations

import subprocess
from typing import Optional

from common.types import CPUCoreData, CPUStats


def _sysctl_int(key: str) -> int | None:
    """Get integer value from sysctl."""
    try:
        result = subprocess.run(
            ["sysctl", "-n", key],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except Exception:
        pass
    return None


def _sysctl_str(key: str) -> str | None:
    """Get string value from sysctl."""
    try:
        result = subprocess.run(
            ["sysctl", "-n", key],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


class CPUCollector:
    """Collects CPU metrics for Apple Silicon.
    
    Uses psutil for per-core load and sysctl for static info.
    No sudo required.
    """

    def __init__(self) -> None:
        self._core_count: int | None = None
        self._cpu_brand: str | None = None
        self._cpu_family: int | None = None
        self._last_loads: list[float] = []

    def _get_core_count(self) -> int:
        """Get logical CPU core count."""
        if self._core_count is None:
            self._core_count = _sysctl_int("hw.ncpu") or 8
        return self._core_count

    def _get_cpu_brand(self) -> str | None:
        """Get CPU brand string (e.g., 'Apple M1 Max')."""
        if self._cpu_brand is None:
            self._cpu_brand = _sysctl_str("machdep.cpu.brand_string")
        return self._cpu_brand

    def collect(self) -> CPUStats:
        """Collect CPU stats using psutil.
        
        Note: psutil.cpu_percent() requires a baseline sample.
        First call returns 0.0 for all cores.
        """
        try:
            import psutil
            
            # Get per-core percentages
            # interval=None uses the time since last call (or since import for first call)
            per_core = psutil.cpu_percent(percpu=True, interval=None)
            
            # Total load
            total_load = sum(per_core) / len(per_core) if per_core else 0.0
            
            # Build core data
            cores: list[CPUCoreData] = []
            for idx, load in enumerate(per_core):
                cores.append(CPUCoreData(
                    index=idx,
                    load_pct=load,
                    # Clock speeds not available via psutil on macOS without sudo
                    eff_clock_mhz=None,
                ))
            
            # Try to get CPU frequency (static value on macOS)
            freq_info = psutil.cpu_freq()
            base_clock = freq_info.current if freq_info else None
            
            return CPUStats(
                total_load_pct=total_load,
                cores=cores,
                available=True,
            )
            
        except ImportError:
            return CPUStats(available=False, error="psutil not installed")
        except Exception as e:
            return CPUStats(available=False, error=str(e))

    def enrich_from_powermetrics(self, cpu: CPUStats, pm_data: dict) -> CPUStats:
        """Enrich CPU stats with powermetrics data (freq, power, temp if available)."""
        if not pm_data or "processor" not in pm_data:
            return cpu
        
        try:
            proc = pm_data["processor"]
            
            # CPU power
            if "cpu_energy" in proc:
                # Energy in mJ over the sample period, convert to W
                # powermetrics gives energy per sample, we need to calculate power
                cpu.power_w = proc.get("cpu_energy", 0) / 1000.0
            
            # Per-core frequencies from clusters
            if "clusters" in proc:
                for cluster in proc["clusters"]:
                    cluster_name = cluster.get("name", "")
                    freq_hz = cluster.get("freq_hz", 0)
                    
                    # Determine which cores belong to this cluster
                    # E-cores: indices 0-3 typically
                    # P-cores: indices 4+ typically
                    if cluster_name.startswith("E"):
                        # E-cluster (efficiency cores)
                        for core in cpu.cores[:4]:
                            core.eff_clock_mhz = freq_hz / 1e6
                    elif cluster_name.startswith("P"):
                        # P-cluster (performance cores)
                        for core in cpu.cores[4:]:
                            core.eff_clock_mhz = freq_hz / 1e6
            
            # CPU temperature not directly available in powermetrics
            # Would need to parse from thermal data or use other sources
            
        except Exception:
            pass
        
        return cpu
