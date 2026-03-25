r"""
NPU metrics via AMD xrt-smi.
Binary: C:\Windows\System32\AMD\xrt-smi.exe

Parses two commands:
  xrt-smi examine               -> XRT/driver/firmware versions
  xrt-smi examine --report aie-partitions  -> partition + context data
"""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field

_XRT_SMI = r"C:\Windows\System32\AMD\xrt-smi.exe"


@dataclass
class NPUContext:
    pid: int
    ctx_id: int
    status: str      # "Idle" | "Running" | ...
    gops: float      # Giga Operations / sec (reported)
    egops: float     # Effective GOPS


@dataclass
class NPUPartition:
    index: int
    columns: list[int] = field(default_factory=list)
    contexts: list[NPUContext] = field(default_factory=list)

    @property
    def active_contexts(self) -> int:
        return sum(1 for c in self.contexts if c.status.lower() != "idle")

    @property
    def total_gops(self) -> float:
        return sum(c.gops for c in self.contexts)

    @property
    def total_egops(self) -> float:
        return sum(c.egops for c in self.contexts)


@dataclass
class NPUStats:
    available: bool = False
    xrt_version: str = ""
    driver_version: str = ""
    firmware_version: str = ""
    partitions: list[NPUPartition] = field(default_factory=list)
    error: str = ""

    @property
    def total_contexts(self) -> int:
        return sum(len(p.contexts) for p in self.partitions)

    @property
    def active_contexts(self) -> int:
        return sum(p.active_contexts for p in self.partitions)

    @property
    def total_gops(self) -> float:
        return sum(p.total_gops for p in self.partitions)

    @property
    def total_egops(self) -> float:
        return sum(p.total_egops for p in self.partitions)


def _run(args: list[str], timeout: int = 5) -> str:
    try:
        r = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return r.stdout + r.stderr
    except Exception:
        return ""


class NPUCollector:
    def __init__(self) -> None:
        self._available = os.path.isfile(_XRT_SMI)
        self._base_info: tuple[str, str, str] = ("", "", "")
        self._base_fetched = False

    def collect(self) -> NPUStats:
        if not self._available:
            return NPUStats(available=False, error="xrt-smi not found")

        # Fetch version info once
        if not self._base_fetched:
            self._base_info = self._parse_base()
            self._base_fetched = True

        xrt_ver, drv_ver, fw_ver = self._base_info

        # Parse partitions every tick
        partitions = self._parse_partitions()

        return NPUStats(
            available=True,
            xrt_version=xrt_ver,
            driver_version=drv_ver,
            firmware_version=fw_ver,
            partitions=partitions,
        )

    def _parse_base(self) -> tuple[str, str, str]:
        out = _run([_XRT_SMI, "examine"])
        xrt = re.search(r"Version\s*:\s*(\S+)", out)
        drv = re.search(r"NPU Driver Version\s*:\s*(\S+)", out)
        fw  = re.search(r"NPU Firmware Version\s*:\s*(\S+)", out)
        return (
            xrt.group(1) if xrt else "",
            drv.group(1) if drv else "",
            fw.group(1)  if fw  else "",
        )

    def _parse_partitions(self) -> list[NPUPartition]:
        out = _run([_XRT_SMI, "examine", "--report", "aie-partitions"])
        partitions: list[NPUPartition] = []
        current: NPUPartition | None = None

        for line in out.splitlines():
            # "  Partition Index: 0"
            m = re.match(r"\s*Partition Index:\s*(\d+)", line)
            if m:
                current = NPUPartition(index=int(m.group(1)))
                partitions.append(current)
                continue

            if current is None:
                continue

            # "    Columns: [0, 1]"
            m = re.match(r"\s*Columns:\s*\[([^\]]+)\]", line)
            if m:
                current.columns = [int(x.strip()) for x in m.group(1).split(",")]
                continue

            # Table row: |14256  |1  |Idle  |8736 KB  |1482  |1482  |0  |0  |Low  |0  |0  |0  |0  |
            # Skip header rows (contain non-numeric PID)
            if line.strip().startswith("|") and "|" in line:
                cols = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cols) >= 10:
                    try:
                        pid    = int(cols[0])
                        ctx_id = int(cols[1])
                        status = cols[2]
                        gops   = float(cols[9])
                        egops  = float(cols[10]) if len(cols) > 10 else 0.0
                        current.contexts.append(
                            NPUContext(pid, ctx_id, status, gops, egops)
                        )
                    except (ValueError, IndexError):
                        pass  # header or malformed row

        return partitions
