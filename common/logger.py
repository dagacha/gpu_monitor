"""CSV logging for system metrics."""
from __future__ import annotations

import csv
import os
import time
from dataclasses import dataclass
from typing import Optional, TextIO

from common.types import SystemSnapshot


@dataclass
class CSVLogger:
    """CSV logger for system metrics.

    Writes a row per tick with timestamp and all metrics.
    """
    log_dir: str = "."
    active: bool = False
    _path: Optional[str] = None
    _file: Optional[TextIO] = None
    _writer: Optional[csv.writer] = None

    def __post_init__(self):
        if self.log_dir:
            os.makedirs(self.log_dir, exist_ok=True)

    @property
    def path(self) -> Optional[str]:
        return self._path

    def toggle(self) -> str:
        """Toggle logging on/off. Returns status message."""
        if self.active:
            self.stop()
            return "CSV logging stopped"
        else:
            self.start()
            return f"CSV logging started: {self._path}"

    def start(self) -> None:
        """Start logging to a new CSV file."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self._path = os.path.join(self.log_dir, f"gpu_monitor_{timestamp}.csv")
        self._file = open(self._path, "w", newline="")
        self._writer = csv.writer(self._file)
        self._writer.writerow([
            "timestamp",
            "gpu_total_util",
            "gpu_temp_c",
            "gpu_clock_mhz",
            "gpu_power_w",
            "gpu_mem_used_mb",
            "gpu_mem_total_mb",
            "cpu_temp_c",
            "cpu_total_load_pct",
            "cpu_power_w",
            "cpu_cores_active",
            "package_power_w",
            "thermal_pressure",
        ])
        self._file.flush()
        self.active = True

    def stop(self) -> None:
        """Stop logging and close file."""
        self.active = False
        if self._file:
            self._file.close()
            self._file = None
            self._writer = None

    def log(self, snapshot: SystemSnapshot) -> None:
        """Write a row to the CSV file."""
        if not self.active or not self._writer:
            return

        gpu = snapshot.gpu
        cpu = snapshot.cpu
        power = snapshot.power

        # Count active cores (load > 5%)
        active_cores = sum(1 for c in cpu.cores if c.load_pct > 5)

        self._writer.writerow([
            time.strftime("%Y-%m-%d %H:%M:%S"),
            f"{gpu.total_utilization:.1f}",
            f"{gpu.temp_c:.0f}" if gpu.temp_c else "",
            f"{gpu.clock_mhz:.0f}" if gpu.clock_mhz else "",
            f"{gpu.power_w:.1f}" if gpu.power_w else "",
            f"{gpu.mem_used_mb:.0f}" if gpu.mem_used_mb else "",
            f"{gpu.mem_total_mb:.0f}" if gpu.mem_total_mb else "",
            f"{cpu.temp_c:.0f}" if cpu.temp_c else "",
            f"{cpu.total_load_pct:.1f}" if cpu.total_load_pct else "",
            f"{cpu.power_w:.1f}" if cpu.power_w else "",
            active_cores,
            f"{power.package_power_w:.1f}" if power.package_power_w else "",
            power.thermal_pressure or "",
        ])
        self._file.flush()
