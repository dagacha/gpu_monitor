"""GPU metrics via nvidia-smi.

Queries utilization, memory, temperature, clocks, power, fan, and PCIe link.
Returns common.types.GPUStats (aggregated across all GPUs; first GPU as primary).
"""
from __future__ import annotations

import subprocess
from typing import Optional

from common.types import GPUStats, GPUEngine

from platforms.nvidia_linux.config import NvidiaConfig


def _run(args: list[str], timeout: int = 5) -> str:
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def _parse_num(s: str, fallback: Optional[float] = None) -> Optional[float]:
    s = s.replace(" MiB", "").replace(" W", "").replace(" MHz", "").replace("%", "").strip()
    if not s:
        return fallback
    try:
        return float(s)
    except ValueError:
        return fallback


def _parse_int(s: str) -> Optional[int]:
    s = s.strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def collect(config: NvidiaConfig | None = None) -> GPUStats:
    """Query nvidia-smi and return GPUStats (primary GPU)."""
    cfg = config or NvidiaConfig()
    query = (
        "name,utilization.gpu,utilization.memory,temperature.gpu,"
        "power.draw,power.limit,clocks.current.graphics,clocks.current.memory,"
        "memory.used,memory.total,fan.speed,"
        "pcie.link.gen.current,pcie.link.width.current"
    )
    output = _run([cfg.NVSMI_PATH, f"--query-gpu={query}", "--format=csv,noheader"])
    if not output:
        return GPUStats(available=False, error="nvidia-smi returned no output")

    lines = output.splitlines()
    if not lines:
        return GPUStats(available=False, error="No GPU detected")

    fields = [c.strip() for c in lines[0].split(",")]

    # Build per-engine dict from utilization.gpu and utilization.memory
    engines: dict[str, float] = {
        "3D": _parse_num(fields[1]) or 0.0,
        "Memory BW": _parse_num(fields[2]) or 0.0,
    }

    mem_used = _parse_num(fields[8]) or 0.0
    mem_total = _parse_num(fields[9]) or 0.0

    return GPUStats(
        total_utilization=_parse_num(fields[1]) or 0.0,
        engines=engines,
        temp_c=_parse_num(fields[3]),
        clock_mhz=_parse_num(fields[6]),
        memory_clock_mhz=_parse_num(fields[7]),
        power_w=_parse_num(fields[4]),
        mem_used_mb=mem_used,
        mem_total_mb=mem_total,
        available=True,
    )
