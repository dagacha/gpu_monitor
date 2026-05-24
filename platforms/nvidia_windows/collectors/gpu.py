"""GPU metrics for NVIDIA on Windows.

Tries NVML (pynvml) first for fast, rich, in-process queries. If pynvml is not
installed or NVML init fails (no driver, no GPU), falls back to nvidia-smi
subprocess calls — same shape as the Linux variant.
"""
from __future__ import annotations

import subprocess
from typing import Optional

from common.types import GPUStats

from platforms.nvidia_windows.config import NvidiaWindowsConfig


class GPUCollector:
    """NVML-first GPU collector with nvidia-smi fallback."""

    def __init__(self, config: NvidiaWindowsConfig | None = None) -> None:
        self.config = config or NvidiaWindowsConfig()
        self._nvml = None
        self._handle = None
        self._gpu_name = "NVIDIA GPU"
        self._init_nvml()

    def _init_nvml(self) -> None:
        try:
            import pynvml
            pynvml.nvmlInit()
            if pynvml.nvmlDeviceGetCount() == 0:
                pynvml.nvmlShutdown()
                return
            self._nvml = pynvml
            self._handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            try:
                name = pynvml.nvmlDeviceGetName(self._handle)
                self._gpu_name = name.decode("utf-8") if isinstance(name, bytes) else str(name)
            except Exception:
                pass
        except Exception:
            self._nvml = None
            self._handle = None

    @property
    def gpu_name(self) -> str:
        return self._gpu_name

    def collect(self) -> GPUStats:
        if self._nvml is not None and self._handle is not None:
            return self._collect_nvml()
        return self._collect_smi()

    def _collect_nvml(self) -> GPUStats:
        nvml = self._nvml
        h = self._handle
        stats = GPUStats(total_utilization=0.0, available=True)

        try:
            util = nvml.nvmlDeviceGetUtilizationRates(h)
            stats.total_utilization = float(util.gpu)
            stats.engines = {
                "3D": float(util.gpu),
                "Memory BW": float(util.memory),
            }
        except Exception:
            pass

        try:
            enc, _ = nvml.nvmlDeviceGetEncoderUtilization(h)
            stats.engines["Encoder"] = float(enc)
        except Exception:
            pass
        try:
            dec, _ = nvml.nvmlDeviceGetDecoderUtilization(h)
            stats.engines["Decoder"] = float(dec)
        except Exception:
            pass

        try:
            mem = nvml.nvmlDeviceGetMemoryInfo(h)
            stats.mem_used_mb = mem.used / (1024 * 1024)
            stats.mem_total_mb = mem.total / (1024 * 1024)
        except Exception:
            pass

        try:
            stats.temp_c = float(nvml.nvmlDeviceGetTemperature(h, nvml.NVML_TEMPERATURE_GPU))
        except Exception:
            pass

        try:
            stats.power_w = nvml.nvmlDeviceGetPowerUsage(h) / 1000.0
        except Exception:
            pass

        try:
            stats.clock_mhz = float(nvml.nvmlDeviceGetClockInfo(h, nvml.NVML_CLOCK_GRAPHICS))
        except Exception:
            pass
        try:
            stats.memory_clock_mhz = float(nvml.nvmlDeviceGetClockInfo(h, nvml.NVML_CLOCK_MEM))
        except Exception:
            pass

        return stats

    def _collect_smi(self) -> GPUStats:
        cfg = self.config
        query = (
            "name,utilization.gpu,utilization.memory,temperature.gpu,"
            "power.draw,clocks.current.graphics,clocks.current.memory,"
            "memory.used,memory.total"
        )
        try:
            r = subprocess.run(
                [cfg.NVSMI_PATH, f"--query-gpu={query}", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except FileNotFoundError:
            return GPUStats(total_utilization=0.0, available=False, error="nvidia-smi not found")
        except Exception as e:
            return GPUStats(total_utilization=0.0, available=False, error=str(e))

        output = r.stdout.strip()
        if not output:
            return GPUStats(total_utilization=0.0, available=False, error="nvidia-smi returned no output")

        first = output.splitlines()[0]
        fields = [c.strip() for c in first.split(",")]
        if len(fields) < 9:
            return GPUStats(total_utilization=0.0, available=False, error="unexpected nvidia-smi output")

        def _num(s: str) -> Optional[float]:
            s = s.strip()
            if not s or s == "[N/A]":
                return None
            try:
                return float(s)
            except ValueError:
                return None

        self._gpu_name = fields[0] or self._gpu_name
        util_gpu = _num(fields[1]) or 0.0
        util_mem = _num(fields[2]) or 0.0
        return GPUStats(
            total_utilization=util_gpu,
            engines={"3D": util_gpu, "Memory BW": util_mem},
            temp_c=_num(fields[3]),
            power_w=_num(fields[4]),
            clock_mhz=_num(fields[5]),
            memory_clock_mhz=_num(fields[6]),
            mem_used_mb=_num(fields[7]) or 0.0,
            mem_total_mb=_num(fields[8]) or 0.0,
            available=True,
        )

    def close(self) -> None:
        if self._nvml is not None:
            try:
                self._nvml.nvmlShutdown()
            except Exception:
                pass
            self._nvml = None
            self._handle = None
