"""Per-process GPU memory via nvidia-smi --query-compute-apps."""
from __future__ import annotations

import os
import subprocess

from common.types import ProcessInfo, ProcessStats

from platforms.nvidia_windows.config import NvidiaWindowsConfig


def collect(config: NvidiaWindowsConfig | None = None) -> ProcessStats:
    cfg = config or NvidiaWindowsConfig()
    try:
        r = subprocess.run(
            [cfg.NVSMI_PATH,
             "--query-compute-apps=pid,process_name,used_memory",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except FileNotFoundError:
        return ProcessStats(available=False, error="nvidia-smi not found")
    except Exception as e:
        return ProcessStats(available=False, error=str(e))

    out = r.stdout.strip()
    if not out:
        return ProcessStats(available=True, processes=[])

    processes: list[ProcessInfo] = []
    for line in out.splitlines():
        fields = [c.strip() for c in line.split(",")]
        if len(fields) < 3:
            continue
        try:
            pid = int(fields[0])
        except ValueError:
            continue
        name = os.path.basename(fields[1]) or fields[1]
        try:
            mem_mb = float(fields[2]) if fields[2] else 0.0
        except ValueError:
            mem_mb = 0.0
        processes.append(
            ProcessInfo(pid=pid, name=name, local_mb=mem_mb, shared_mb=0.0, total_mb=mem_mb)
        )

    processes.sort(key=lambda p: p.total_mb, reverse=True)
    return ProcessStats(processes=processes[:20], available=True)
