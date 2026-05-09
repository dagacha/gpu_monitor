"""AMD Ryzen collectors — orchestrates all data sources into a SystemSnapshot."""
from __future__ import annotations

import time
from typing import Optional

from common.types import (
    CPUStats,
    GPUStats,
    MemoryRow,
    MemoryStats,
    PowerStats,
    ProcessStats,
    SystemSnapshot,
)
from platforms.amd_ryzen.collectors.gpu_pdh import GPUPDHCollector
from platforms.amd_ryzen.collectors.hw_monitor import HWMonitorCollector
from platforms.amd_ryzen.collectors.npu import NPUCollector, NPUStats
from platforms.amd_ryzen.collectors.process_gpu import ProcessGPUCollector


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
            pass

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
            used = gpu.mem_shared_mb
            total = gpu.mem_shared_total_mb or 16384.0  # Default 16GB if unknown
            pct = (used / total * 100) if total > 0 else 0.0
            memory_rows.append(MemoryRow(
                label="GPU Shared",
                used_mb=used,
                total_mb=total,
                pct=min(pct, 100.0),
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
        self._processes.close()


# Convenience function for direct import
collect_all = AMDRyzenCollectors().collect
