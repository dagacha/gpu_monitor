"""CPU and system memory via psutil + sysfs.

Returns common.types.CPUStats and common.types.MemoryStats.
"""
from __future__ import annotations

import os

from common.debug import get_logger
from common.types import CPUCoreData, CPUStats, MemoryRow, MemoryStats

from platforms.nvidia_linux.config import NvidiaConfig

_log = get_logger("nvidia_linux.cpu")


def _read_sys(path: str) -> float | None:
    try:
        with open(path) as f:
            return float(f.read().strip()) / 1000.0
    except Exception:
        _log.debug("failed to read %s", path, exc_info=True)
        return None


def _read_cpu_temp() -> float | None:
    """Try k10temp, coretemp, or acpi hwmon sensors."""
    hwmon_dir = "/sys/class/hwmon"
    try:
        for entry in os.listdir(hwmon_dir):
            name_path = os.path.join(hwmon_dir, entry, "name")
            if os.path.isfile(name_path):
                with open(name_path) as f:
                    name = f.read().strip()
                if name in ("k10temp", "k10temp_pvt", "coretemp", "acpi_thermal"):
                    val = _read_sys(os.path.join(hwmon_dir, entry, "temp1_input"))
                    if val is not None:
                        return val
    except Exception:
        _log.debug("failed to read cpu temp from hwmon", exc_info=True)
    return None


def _read_cpu_freq() -> float | None:
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("cpu MHz"):
                    parts = line.split(":")
                    if len(parts) > 1:
                        return float(parts[1].strip())
    except Exception:
        _log.debug("failed to read cpu freq from /proc/cpuinfo", exc_info=True)
    return None


def collect_cpu(config: NvidiaConfig | None = None) -> CPUStats:
    import psutil

    per_core = psutil.cpu_percent(percpu=True, interval=None)
    total_load = sum(per_core) / len(per_core) if per_core else 0.0

    cores: list[CPUCoreData] = []
    for idx, load in enumerate(per_core):
        cores.append(CPUCoreData(index=idx, load_pct=load))

    return CPUStats(
        total_load_pct=total_load,
        temp_c=_read_cpu_temp(),
        power_w=None,
        cores=cores,
        available=True,
    )


def collect_memory(config: NvidiaConfig | None = None) -> MemoryStats:
    import psutil

    vm = psutil.virtual_memory()
    sm = psutil.swap_memory()

    total_mb = vm.total / (1024 * 1024)
    used_mb = vm.used / (1024 * 1024)

    rows: list[MemoryRow] = [
        MemoryRow(
            label="System RAM",
            used_mb=used_mb,
            total_mb=total_mb,
            pct=vm.percent,
        ),
    ]

    if sm.total > 0:
        swap_mb = sm.used / (1024 * 1024)
        swap_total = sm.total / (1024 * 1024)
        rows.append(
            MemoryRow(
                label="Swap",
                used_mb=swap_mb,
                total_mb=swap_total,
                pct=(swap_mb / swap_total * 100) if swap_total > 0 else 0,
            )
        )

    return MemoryStats(rows=rows, available=True)
