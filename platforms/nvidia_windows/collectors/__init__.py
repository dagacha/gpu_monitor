"""NVIDIA Windows collectors — orchestrates all data sources into a SystemSnapshot."""
from __future__ import annotations

import time

from common.types import PowerStats, SystemSnapshot

from platforms.nvidia_windows.collectors.gpu_nvml import GPUNVMLCollector
from platforms.nvidia_windows.collectors.cpu import collect_cpu, collect_memory
from platforms.nvidia_windows.collectors.cpu_lhm import CPULHMCollector
from platforms.nvidia_windows.collectors.process_pdh import ProcessPDHCollector
from platforms.nvidia_windows.config import NvidiaConfig


class NvidiaWindowsCollectors:
    """Orchestrates all NVIDIA Windows data collectors.

    Data sources:
    - NVML (pynvml): GPU utilization, memory, temp, clocks, power, PCIe,
      encoder/decoder, throttle reasons (nvidia-smi fallback)
    - PDH: per-process GPU memory and utilization (nvidia-smi fallback)
    - psutil: CPU per-core load, system RAM
    - LibreHardwareMonitor: CPU temperature and package power
      (requires an elevated terminal for the sensor driver)
    """

    def __init__(self, config: NvidiaConfig | None = None) -> None:
        self.config = config or NvidiaConfig()
        self.gpu = GPUNVMLCollector(self.config)
        self.processes = ProcessPDHCollector(self.config)
        self.cpu_lhm = CPULHMCollector(self.config)

    @property
    def gpu_name(self) -> str:
        return self.gpu.gpu_name

    def collect(self) -> SystemSnapshot:
        gpu = self.gpu.collect()
        cpu = self.cpu_lhm.enrich(collect_cpu(self.config))
        memory = collect_memory(self.config)
        processes = self.processes.collect()
        power = PowerStats(
            cpu_power_w=cpu.power_w,
            gpu_power_w=gpu.power_w,
            available=gpu.power_w is not None or cpu.power_w is not None,
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
        self.gpu.close()
        self.processes.close()
        self.cpu_lhm.close()


def collect_all(config: NvidiaConfig | None = None) -> SystemSnapshot:
    collectors = NvidiaWindowsCollectors(config)
    try:
        return collectors.collect()
    finally:
        collectors.close()
