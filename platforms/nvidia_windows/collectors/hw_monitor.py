"""CPU sensor data for NVIDIA Windows platform.

Reuses the AMD platform's LibreHardwareMonitor bridge for temp/clock/power, then
backfills per-core load and total load from psutil — LHM's per-core load is
spotty on some Intel chips, and we always want a populated cores list for the
CPU panel.
"""
from __future__ import annotations

from common.types import CPUCoreData, CPUStats

from platforms.amd_ryzen.collectors.hw_monitor import HWMonitorCollector as _LHMCollector


class CPUHWMonitorCollector:
    """CPU stats from LHM + psutil."""

    def __init__(self) -> None:
        self._lhm = _LHMCollector()

    def collect(self) -> CPUStats:
        cpu = self._lhm.collect()

        try:
            import psutil
            per_core = psutil.cpu_percent(percpu=True, interval=None)
        except Exception:
            per_core = []

        if per_core:
            existing = {c.index: c for c in cpu.cores}
            cores: list[CPUCoreData] = []
            for idx, load in enumerate(per_core):
                cd = existing.get(idx, CPUCoreData(index=idx))
                cd.load_pct = float(load)
                cores.append(cd)
            cpu.cores = cores
            if cpu.total_load_pct is None:
                cpu.total_load_pct = sum(per_core) / len(per_core)

        if not cpu.available and (cpu.cores or cpu.total_load_pct is not None):
            cpu.available = True

        return cpu
