"""NVIDIA Windows collectors — orchestrates all data sources into a SystemSnapshot."""
from __future__ import annotations

import time

from common.types import PowerStats, SystemSnapshot

from platforms.nvidia_windows.collectors.gpu import collect as collect_gpu
from platforms.nvidia_windows.collectors.cpu import collect_cpu, collect_memory
from platforms.nvidia_windows.collectors.process import collect as collect_processes
from platforms.nvidia_windows.config import NvidiaConfig


class NvidiaWindowsCollectors:
    """Orchestrates all NVIDIA Windows data collectors.

    Data sources:
    - nvidia-smi: GPU utilization, memory, temp, clocks, power, PCIe
    - psutil: CPU per-core load, system RAM
    """

    def __init__(self, config: NvidiaConfig | None = None) -> None:
        self.config = config or NvidiaConfig()

    def collect(self) -> SystemSnapshot:
        gpu = collect_gpu(self.config)
        cpu = collect_cpu(self.config)
        memory = collect_memory(self.config)
        processes = collect_processes(self.config)
        power = PowerStats(
            gpu_power_w=gpu.power_w,
            available=gpu.power_w is not None,
        )

        return SystemSnapshot(
            gpu=gpu,
            cpu=cpu,
            memory=memory,
            power=power,
            processes=processes,
            timestamp=time.time(),
        )


def collect_all(config: NvidiaConfig | None = None) -> SystemSnapshot:
    return NvidiaWindowsCollectors(config).collect()
