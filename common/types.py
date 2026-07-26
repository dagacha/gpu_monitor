"""Shared types for gpu_monitor across all platforms."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GPUEngine:
    """A single GPU engine (e.g., 3D, Compute, Copy)."""
    name: str
    utilization: float  # 0-100%


@dataclass
class GPUStats:
    """GPU metrics from any platform."""
    total_utilization: float  # 0-100%
    engines: dict[str, float] = field(default_factory=dict)  # engine_name -> %
    temp_c: Optional[float] = None
    clock_mhz: Optional[float] = None
    memory_clock_mhz: Optional[float] = None
    power_w: Optional[float] = None
    mem_used_mb: Optional[float] = None
    mem_total_mb: Optional[float] = None
    mem_shared_mb: Optional[float] = None
    mem_shared_total_mb: Optional[float] = None
    fan_pct: Optional[float] = None
    power_limit_w: Optional[float] = None
    pcie_gen: Optional[int] = None
    pcie_width: Optional[int] = None
    pcie_tx_mb_s: Optional[float] = None
    pcie_rx_mb_s: Optional[float] = None
    throttle_reasons: list[str] = field(default_factory=list)
    available: bool = False
    error: str = ""


@dataclass
class CPUCoreData:
    """Per-core CPU metrics."""
    index: int
    load_pct: float = 0.0
    eff_clock_mhz: Optional[float] = None
    base_clock_mhz: Optional[float] = None
    power_w: Optional[float] = None


@dataclass
class CPUStats:
    """CPU metrics from any platform."""
    temp_c: Optional[float] = None
    total_load_pct: Optional[float] = None
    cores: list[CPUCoreData] = field(default_factory=list)
    power_w: Optional[float] = None
    available: bool = False
    error: str = ""


@dataclass
class MemoryRow:
    """A single memory row for display."""
    label: str
    used_mb: float
    total_mb: Optional[float] = None
    pct: float = 0.0


@dataclass
class MemoryStats:
    """Memory metrics from any platform."""
    rows: list[MemoryRow] = field(default_factory=list)
    available: bool = False
    error: str = ""


@dataclass
class PowerStats:
    """Power and thermal metrics from any platform."""
    cpu_power_w: Optional[float] = None
    gpu_power_w: Optional[float] = None
    package_power_w: Optional[float] = None
    soc_power_w: Optional[float] = None
    thermal_pressure: Optional[str] = None  # "Nominal" | "Fair" | "Serious" | "Critical"
    available: bool = False
    error: str = ""


@dataclass
class ProcessInfo:
    """Per-process GPU memory info."""
    pid: int
    name: str
    local_mb: float
    shared_mb: float
    total_mb: float
    gpu_util_pct: Optional[float] = None


@dataclass
class ProcessStats:
    """Process list with GPU memory usage."""
    processes: list[ProcessInfo] = field(default_factory=list)
    available: bool = False
    error: str = ""


@dataclass
class SystemSnapshot:
    """Complete system snapshot for one refresh tick."""
    gpu: GPUStats
    cpu: CPUStats
    memory: MemoryStats
    power: PowerStats
    processes: ProcessStats
    processes_by_memory: ProcessStats = field(default_factory=lambda: ProcessStats())
    timestamp: float = 0.0
