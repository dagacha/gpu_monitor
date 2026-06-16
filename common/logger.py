"""
CSV logger — records GPU/CPU/Memory stats to a timestamped CSV file.

Toggle with the 'l' key in any platform app.
Works with SystemSnapshot from common.types, so the same logger works
across AMD Ryzen, NVIDIA, and Apple Silicon platforms.
"""
from __future__ import annotations

import csv
import os
import time
from typing import Optional, TextIO

from common.types import SystemSnapshot


class CSVLogger:
    """CSV logger for system metrics.

    Writes one row per tick with a fixed base set of columns plus
    per-GPU-engine columns that are resolved lazily on the first tick
    (so different platforms end up with the columns they actually have).
    """

    def __init__(self, log_dir: str = ".") -> None:
        self._log_dir = log_dir
        self._file: Optional[TextIO] = None
        self._writer: Optional[csv.writer] = None
        self._active = False
        self._path: str = ""
        self._header_written = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def active(self) -> bool:
        return self._active

    @property
    def path(self) -> str:
        return self._path

    def toggle(self) -> str:
        """Toggle logging on/off.  Returns a human-readable status message."""
        if self._active:
            self.stop()
            return f"Logging stopped — {self._path}"
        self.start()
        return f"Logging → {self._path}"

    def start(self) -> None:
        """Open a new CSV file for writing."""
        ts = time.strftime("%Y%m%d_%H%M%S")
        os.makedirs(self._log_dir, exist_ok=True)
        self._path = os.path.join(self._log_dir, f"gpu_log_{ts}.csv")
        self._file = open(self._path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        self._header_written = False
        self._active = True

    def stop(self) -> None:
        """Flush and close the file."""
        self._active = False
        if self._file:
            self._file.close()
        self._file = None
        self._writer = None

    def log(self, snapshot: SystemSnapshot) -> None:
        """Write one row to the CSV.

        The header is emitted lazily on the first call so we can
        discover the actual engine names available in this snapshot.
        """
        if not self._active or self._writer is None:
            return

        row = self._build_row(snapshot)

        if not self._header_written:
            header = list(self._base_header()) + list(self._engine_header(snapshot))
            self._writer.writerow(header)
            self._header_written = True

        self._writer.writerow(row)
        self._file.flush()  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Header helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _base_header() -> list[str]:
        """Columns that are always present regardless of platform."""
        return [
            "timestamp",
            # GPU
            "gpu_total_pct",
            "gpu_temp_c",
            "gpu_clock_mhz",
            "gpu_mem_clock_mhz",
            "gpu_power_w",
            "gpu_mem_used_mb",
            "gpu_mem_total_mb",
            # CPU
            "cpu_temp_c",
            "cpu_power_w",
            "cpu_total_pct",
            # Power / SoC
            "package_power_w",
            "thermal_pressure",
            # Memory (first row only — System RAM / unified)
            "sys_ram_used_mb",
            "sys_ram_total_mb",
            "swap_used_mb",
            "swap_total_mb",
        ]

    @staticmethod
    def _engine_header(snapshot: SystemSnapshot) -> list[str]:
        """Per-GPU-engine columns — names are discovered from the snapshot."""
        gpu = snapshot.gpu
        if not gpu or not gpu.available or not gpu.engines:
            return []
        return [f"gpu_engine_{name}_pct" for name in sorted(gpu.engines)]

    # ------------------------------------------------------------------
    # Row builder
    # ------------------------------------------------------------------

    def _build_row(self, snapshot: SystemSnapshot) -> list:
        gpu = snapshot.gpu
        cpu = snapshot.cpu
        power = snapshot.power

        # Memory: find the primary RAM row and swap (if any)
        sys_ram_used = sys_ram_total = swap_used = swap_total = ""
        if snapshot.memory and snapshot.memory.available:
            for row in snapshot.memory.rows:
                label = row.label.strip().lower()
                if label in ("system ram", "cpu dedicated"):
                    sys_ram_used = _fmt(row.used_mb, 0)
                    sys_ram_total = _fmt(row.total_mb, 0)
                elif label == "swap":
                    swap_used = _fmt(row.used_mb, 0)
                    swap_total = _fmt(row.total_mb, 0)

        base = [
            time.strftime("%Y-%m-%d %H:%M:%S"),
            # GPU
            _fmt(gpu.total_utilization, 1),
            _fmt(gpu.temp_c, 0),
            _fmt(gpu.clock_mhz, 0),
            _fmt(gpu.memory_clock_mhz, 0),
            _fmt(gpu.power_w, 1),
            _fmt(gpu.mem_used_mb, 0),
            _fmt(gpu.mem_total_mb, 0),
            # CPU
            _fmt(cpu.temp_c, 0),
            _fmt(cpu.power_w, 1),
            _fmt(cpu.total_load_pct, 1),
            # Power
            _fmt(power.package_power_w, 1),
            power.thermal_pressure or "",
            # Memory
            sys_ram_used,
            sys_ram_total,
            swap_used,
            swap_total,
        ]

        # Engine columns (order must match _engine_header)
        if gpu and gpu.available and gpu.engines:
            for name in sorted(gpu.engines):
                base.append(_fmt(gpu.engines[name], 1))

        return base


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _fmt(value: object, decimals: int) -> str:
    """Format a numeric value to a fixed number of decimal places.

    Returns empty string for None / zero.
    """
    if value is None:
        return ""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ""
    if decimals == 0:
        return f"{v:.0f}"
    return f"{v:.{decimals}f}"
