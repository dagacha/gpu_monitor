"""Per-process GPU memory via nvidia-smi --query-compute-apps.

Returns common.types.ProcessStats.
"""
from __future__ import annotations

import subprocess

from common.debug import get_logger
from common.types import ProcessInfo, ProcessStats

from platforms.nvidia_linux.config import NvidiaConfig

_log = get_logger("nvidia_linux.process")


def collect(config: NvidiaConfig | None = None) -> ProcessStats:
    cfg = config or NvidiaConfig()
    try:
        r = subprocess.run(
            [cfg.NVSMI_PATH, "--query-compute-apps=pid,name,used_memory",
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception as e:
        _log.debug("nvidia-smi compute-apps query failed", exc_info=True)
        return ProcessStats(available=False, error=str(e))

    if not r.stdout.strip():
        return ProcessStats(available=True, processes=[])

    processes: list[ProcessInfo] = []
    for line in r.stdout.strip().splitlines():
        fields = [c.strip() for c in line.split(",")]
        if len(fields) < 3:
            continue
        try:
            pid = int(fields[0])
        except ValueError:
            continue
        name = fields[1]
        try:
            mem_str = fields[2].replace(" MiB", "").strip()
            mem_mb = float(mem_str) if mem_str else 0.0
        except ValueError:
            mem_mb = 0.0
        processes.append(
            ProcessInfo(pid=pid, name=name, local_mb=mem_mb, shared_mb=0.0, total_mb=mem_mb)
        )

    processes.sort(key=lambda p: p.total_mb, reverse=True)
    return ProcessStats(processes=processes[:20], available=True)
