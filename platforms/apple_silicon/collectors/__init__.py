"""Apple Silicon collectors — orchestrates all data sources into a SystemSnapshot."""
from __future__ import annotations

import time
from typing import Optional

from common.types import (
    CPUStats,
    GPUStats,
    MemoryStats,
    PowerStats,
    ProcessStats,
    SystemSnapshot,
)
from platforms.apple_silicon.collectors.cpu import CPUCollector
from platforms.apple_silicon.collectors.gpu import GPUCollector
from platforms.apple_silicon.collectors.memory import MemoryCollector
from platforms.apple_silicon.collectors.power import PowerCollector
from platforms.apple_silicon.collectors.powermetrics import PowerMetricsRunner
from platforms.apple_silicon.collectors.process import ProcessCollector
from platforms.apple_silicon.config import AppleConfig


class AppleSiliconCollectors:
    """Orchestrates all Apple Silicon data collectors.
    
    Data sources:
    - psutil/vm_stat: CPU, Memory (no sudo)
    - powermetrics: GPU, Power, Thermal (requires sudo)
    
    Returns a unified SystemSnapshot.
    """

    def __init__(self, config: AppleConfig | None = None) -> None:
        self.config = config or AppleConfig()
        
        # Individual collectors
        self._cpu = CPUCollector()
        self._gpu = GPUCollector()
        self._memory = MemoryCollector()
        self._power = PowerCollector()
        self._processes = ProcessCollector()
        
        # powermetrics runner (for GPU/power/thermal)
        self._pm_runner = PowerMetricsRunner(self.config)
        self._has_sudo: bool | None = None

    def _check_sudo(self) -> bool:
        """Check if we have sudo access (cached)."""
        if self._has_sudo is None:
            self._has_sudo = self._pm_runner.can_run_with_sudo()
        return self._has_sudo

    def collect(self) -> SystemSnapshot:
        """Collect all metrics and return SystemSnapshot.
        
        Collects:
        1. CPU (always available via psutil)
        2. Memory (always available via psutil/vm_stat)
        3. powermetrics data (if sudo available) → GPU, Power
        
        Returns:
            SystemSnapshot with all available data
        """
        # Collect always-available data first
        cpu = self._cpu.collect()
        memory = self._memory.collect()
        
        # Try to get powermetrics data (requires sudo)
        pm_data: dict | None = None
        if self._check_sudo():
            pm_data = self._pm_runner.sample()
        
        # GPU requires powermetrics
        if pm_data:
            gpu = self._gpu.collect(pm_data)
        else:
            gpu = self._gpu.collect_basic()
        
        # Power/thermal (uses powermetrics if available, else fallback)
        if pm_data:
            power = self._power.collect(pm_data)
            # Enrich CPU with powermetrics data
            cpu = self._cpu.enrich_from_powermetrics(cpu, pm_data)
        else:
            power = self._power.collect_basic()
        
        # Process stats (top CPU processes via psutil)
        processes = self._processes.collect()
        
        return SystemSnapshot(
            gpu=gpu,
            cpu=cpu,
            memory=memory,
            power=power,
            processes=processes,
            timestamp=time.time(),
        )

    def get_sudo_hint(self) -> str | None:
        """Return hint message if sudo is not configured."""
        if not self._check_sudo():
            return (
                "For GPU, power, and thermal data, run: "
                "sudo powermetrics --samplers cpu_power,gpu_power,thermal "
                "-i 1000 -n 1 once to authorize, then run this app again."
            )
        return None


# Convenience function for direct import
def collect_all(config: AppleConfig | None = None) -> SystemSnapshot:
    """Convenience function to collect all metrics."""
    return AppleSiliconCollectors(config).collect()
