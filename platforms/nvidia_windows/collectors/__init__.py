"""NVIDIA Windows collectors — orchestrates all data sources into a SystemSnapshot."""
from __future__ import annotations

import time

from common.types import MemoryRow, MemoryStats, PowerStats, SystemSnapshot

from platforms.nvidia_windows.collectors.gpu import GPUCollector
from platforms.nvidia_windows.collectors.hw_monitor import CPUHWMonitorCollector
from platforms.nvidia_windows.collectors.process import collect as collect_processes
from platforms.nvidia_windows.config import NvidiaWindowsConfig


class NvidiaWindowsCollectors:
    """Orchestrates NVIDIA Windows data collectors.

    Data sources:
    - NVML (pynvml) primary, nvidia-smi fallback: GPU util, mem, temp, clocks, power
    - LibreHardwareMonitor: CPU temp/clock/power
    - psutil: per-core CPU load, system RAM
    - nvidia-smi --query-compute-apps: per-process GPU memory
    """

    def __init__(self, config: NvidiaWindowsConfig | None = None) -> None:
        self.config = config or NvidiaWindowsConfig()
        self._gpu = GPUCollector(self.config)
        self._cpu_hw = CPUHWMonitorCollector()

    def collect(self) -> SystemSnapshot:
        gpu = self._gpu.collect()
        cpu = self._cpu_hw.collect()
        processes = collect_processes(self.config)

        memory_rows: list[MemoryRow] = []
        try:
            import psutil
            vm = psutil.virtual_memory()
            memory_rows.append(MemoryRow(
                label="System RAM",
                used_mb=vm.used / (1024 * 1024),
                total_mb=vm.total / (1024 * 1024),
                pct=vm.percent,
            ))
        except Exception:
            pass

        if gpu.mem_used_mb is not None and gpu.mem_total_mb is not None and gpu.mem_total_mb > 0:
            memory_rows.append(MemoryRow(
                label="GPU VRAM",
                used_mb=gpu.mem_used_mb,
                total_mb=gpu.mem_total_mb,
                pct=min(gpu.mem_used_mb / gpu.mem_total_mb * 100.0, 100.0),
            ))

        memory = MemoryStats(rows=memory_rows, available=len(memory_rows) > 0)

        power = PowerStats(
            cpu_power_w=cpu.power_w,
            gpu_power_w=gpu.power_w,
            package_power_w=(cpu.power_w or 0.0) + (gpu.power_w or 0.0) if (cpu.power_w or gpu.power_w) else None,
            available=cpu.power_w is not None or gpu.power_w is not None,
        )

        return SystemSnapshot(
            gpu=gpu,
            cpu=cpu,
            memory=memory,
            power=power,
            processes=processes,
            timestamp=time.time(),
        )

    def close(self) -> None:
        self._gpu.close()


def collect_all(config: NvidiaWindowsConfig | None = None) -> SystemSnapshot:
    return NvidiaWindowsCollectors(config).collect()
