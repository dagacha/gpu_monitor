"""
CSV logger — records GPU/CPU/NPU stats to a timestamped CSV file.
Toggle with the 'l' key in the app.
"""
from __future__ import annotations

import csv
import datetime
import os


class CSVLogger:
    def __init__(self) -> None:
        self._file = None
        self._writer = None
        self._active = False
        self._path: str = ""

    # ------------------------------------------------------------------

    def toggle(self) -> str:
        if self._active:
            self.stop()
            return f"Logging stopped — {self._path}"
        else:
            self.start()
            return f"Logging → {self._path}"

    def start(self) -> None:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self._path = os.path.join(os.getcwd(), f"gpu_log_{ts}.csv")
        self._file = open(self._path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        self._writer.writerow([
            "timestamp",
            "gpu_total_pct", "gpu_3d_pct", "gpu_compute_pct",
            "gpu_copy_pct", "gpu_video_pct",
            "gpu_temp_c", "gpu_clock_mhz", "gpu_mem_clock_mhz",
            "gpu_soc_clock_mhz", "gpu_power_w",
            "gpu_mem_used_mb", "gpu_mem_total_mb",
            "cpu_temp_c", "cpu_power_w", "cpu_total_pct",
            "soc_power_w",
            "npu_power_mode",
            "sys_ram_used_gb", "sys_ram_total_gb",
        ])
        self._active = True

    def stop(self) -> None:
        self._active = False
        if self._file:
            self._file.close()
        self._file = None
        self._writer = None

    def log(self, gpu_stats, hw_stats, npu_stats) -> None:
        if not self._active or self._writer is None:
            return
        import psutil
        vm = psutil.virtual_memory()

        d3d = hw_stats.d3d_loads if hw_stats else {}
        by_engine = {e.name: e.utilization for e in (gpu_stats.engines if gpu_stats else [])}

        def _g(src, attr):
            return getattr(src, attr, "") if src else ""

        self._writer.writerow([
            datetime.datetime.now().isoformat(timespec="seconds"),
            # GPU utilization
            _g(hw_stats, "gpu_core_load_pct") or _g(gpu_stats, "total_utilization"),
            d3d.get("3D", by_engine.get("3D", "")),
            d3d.get("Compute 0", by_engine.get("Compute", "")),
            d3d.get("Copy", by_engine.get("Copy", "")),
            d3d.get("Video Codec Engine", by_engine.get("Video", "")),
            # GPU hardware
            _g(hw_stats, "gpu_temp_c"),
            _g(hw_stats, "gpu_clock_mhz"),
            _g(hw_stats, "gpu_memory_clock_mhz"),
            _g(hw_stats, "gpu_soc_clock_mhz"),
            _g(hw_stats, "gpu_power_w"),
            _g(hw_stats, "gpu_mem_used_mb"),
            _g(hw_stats, "gpu_mem_total_mb"),
            # CPU
            _g(hw_stats, "cpu_temp_c"),
            _g(hw_stats, "cpu_power_w"),
            _g(hw_stats, "cpu_total_load_pct"),
            _g(hw_stats, "soc_power_w"),
            # NPU
            npu_stats.power_mode if npu_stats and npu_stats.available else "",
            # System RAM
            f"{vm.used / 1024**3:.2f}",
            f"{vm.total / 1024**3:.2f}",
        ])
        self._file.flush()

    @property
    def active(self) -> bool:
        return self._active

    @property
    def path(self) -> str:
        return self._path
