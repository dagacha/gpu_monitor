"""AMD Ryzen collectors — orchestrates all data sources into a SystemSnapshot."""
from __future__ import annotations

import time
from typing import Optional

from common.debug import get_logger
from common.types import (
    CPUStats,
    GPUStats,
    MemoryRow,
    MemoryStats,
    PowerStats,
    ProcessStats,
    SystemSnapshot,
)
from platforms.amd_ryzen.collectors.gpu_d3dkmt import GPUD3DKMTCollector
from platforms.amd_ryzen.collectors.gpu_pdh import GPUPDHCollector
from platforms.amd_ryzen.collectors.hw_monitor import HWMonitorCollector
from platforms.amd_ryzen.collectors.npu import NPUCollector, NPUStats
from platforms.amd_ryzen.collectors.process_gpu import ProcessGPUCollector

_log = get_logger("amd.collectors")


class AMDRyzenCollectors:
    """Orchestrates all AMD Ryzen data collectors.
    
    Merges data from multiple sources:
    - GPU PDH counters (utilization, memory via D3D)
    - LibreHardwareMonitor (CPU, GPU temps/clocks/power)
    - XRT-SMI (NPU, AMD-specific)
    - PDH process memory (per-process GPU memory)
    
    Returns a unified SystemSnapshot.
    """

    def __init__(self) -> None:
        self._gpu_pdh = GPUPDHCollector()
        self._gpu_d3dkmt = GPUD3DKMTCollector()
        self._hw = HWMonitorCollector()
        self._npu = NPUCollector()
        self._processes = ProcessGPUCollector()
        self._error: Optional[str] = None

    def collect(self) -> tuple[SystemSnapshot, NPUStats]:
        """Collect all metrics and return SystemSnapshot + NPU data.
        
        Returns:
            Tuple of (SystemSnapshot, NPUStats) — NPU is separate because
            it's AMD-specific and not part of the shared types.
        """
        # Collect from all sources
        gpu_pdh = self._gpu_pdh.collect()
        cpu = self._hw.collect()
        processes = self._processes.collect()
        npu = self._npu.collect()

        # Start with PDH GPU data and enrich with LHM
        gpu = self._hw.enrich_gpu(gpu_pdh)

        # WDDM kernel API: authoritative temp/power for adapters LHM cannot read
        # (e.g. Strix Halo iGPU). Always preferred for temperature; only fills
        # other fields when LHM hasn't already provided them.
        perf = self._gpu_d3dkmt.collect()
        if perf is not None:
            if perf.temp_c is not None:
                gpu.temp_c = perf.temp_c
            if gpu.memory_clock_mhz is None and perf.memory_clock_mhz:
                gpu.memory_clock_mhz = perf.memory_clock_mhz

        # Build power stats from LHM
        power = self._hw.enrich_power(PowerStats())

        # Build memory stats from GPU data
        memory_rows: list[MemoryRow] = []

        # CPU Dedicated (system RAM via psutil)
        try:
            import psutil
            vm = psutil.virtual_memory()
            total_mb = vm.total / (1024 * 1024)
            used_mb = vm.used / (1024 * 1024)
            memory_rows.append(MemoryRow(
                label="CPU Dedicated",
                used_mb=used_mb,
                total_mb=total_mb,
                pct=min(vm.percent, 100.0),
            ))
        except Exception:
            _log.debug("failed to read system RAM via psutil", exc_info=True)

        # GPU Dedicated
        if gpu.mem_used_mb is not None and gpu.mem_total_mb is not None:
            used = gpu.mem_used_mb
            total = gpu.mem_total_mb
            pct = (used / total * 100) if total > 0 else 0.0
            memory_rows.append(MemoryRow(
                label="GPU Dedicated",
                used_mb=used,
                total_mb=total,
                pct=min(pct, 100.0),
            ))
        
        # GPU Shared
        if gpu.mem_shared_mb is not None:
            shared_used = gpu.mem_shared_mb
            shared_total = gpu.mem_shared_total_mb  # often None on UMA
            if shared_total and shared_total > 0:
                shared_pct = (shared_used / shared_total) * 100.0
            else:
                shared_pct = 0.0
            memory_rows.append(MemoryRow(
                label="GPU Shared",
                used_mb=shared_used,
                total_mb=shared_total,  # None when upstream couldn't report
                pct=min(shared_pct, 100.0),
            ))

        memory = MemoryStats(rows=memory_rows, available=len(memory_rows) > 0)

        snapshot = SystemSnapshot(
            gpu=gpu,
            cpu=cpu,
            memory=memory,
            power=power,
            processes=processes,
            timestamp=time.time(),
        )

        return snapshot, npu

    def close(self) -> None:
        """Clean up resources."""
        self._gpu_pdh.close()
        self._gpu_d3dkmt.close()
        self._processes.close()


# Convenience function for direct import
def collect_all() -> tuple[SystemSnapshot, NPUStats]:
    return AMDRyzenCollectors().collect()
