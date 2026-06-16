"""CPU and system memory via psutil on Windows.

Returns common.types.CPUStats and common.types.MemoryStats.
"""
from __future__ import annotations

from common.debug import get_logger
from common.types import CPUCoreData, CPUStats, MemoryRow, MemoryStats

from platforms.nvidia_windows.config import NvidiaConfig

_log = get_logger("nvidia_windows.cpu")


def collect_cpu(config: NvidiaConfig | None = None) -> CPUStats:
    import psutil

    per_core = psutil.cpu_percent(percpu=True, interval=None)
    total_load = sum(per_core) / len(per_core) if per_core else 0.0

    cores: list[CPUCoreData] = []
    for idx, load in enumerate(per_core):
        cores.append(CPUCoreData(index=idx, load_pct=load))

    # Try to get CPU temperature (may not be available on all systems)
    temp_c = None
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            # Try common sensor names
            for name in ("coretemp", "k10temp", "acpitz", "cpu_thermal"):
                if name in temps and temps[name]:
                    temp_c = temps[name][0].current
                    break
    except Exception:
        _log.debug("failed to read cpu temperature", exc_info=True)

    return CPUStats(
        total_load_pct=total_load,
        temp_c=temp_c,
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
