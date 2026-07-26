"""GPU metrics via NVML (nvidia-ml-py) on Windows.

In-process driver API — no nvidia-smi subprocess per sample. Adds fields the
CSV query path does not expose: encoder/decoder utilization, throttle reasons,
PCIe TX/RX throughput, and enforced power limit.

Falls back to the nvidia-smi collector when pynvml is unavailable.
"""
from __future__ import annotations

from typing import Optional

from common.debug import get_logger
from common.types import GPUStats

from platforms.nvidia_windows.config import NvidiaConfig
from platforms.nvidia_windows.collectors.gpu import collect as _smi_collect

try:
    import pynvml
    _NVML_AVAILABLE = True
except ImportError:
    _NVML_AVAILABLE = False

_log = get_logger("nvidia_windows.gpu_nvml")

# Throttle-reason bitmask -> human label. Idle/applications-clocks are normal
# operating states, not throttling, so they are intentionally omitted.
# Built once at module level so it is not re-allocated every tick.
if _NVML_AVAILABLE:
    _THROTTLE_LABELS: list[tuple[int, str]] = [
        (pynvml.nvmlClocksThrottleReasonSwPowerCap, "Power cap"),
        (pynvml.nvmlClocksThrottleReasonSwThermalSlowdown, "Thermal (sw)"),
        (pynvml.nvmlClocksThrottleReasonHwThermalSlowdown, "Thermal (hw)"),
        (pynvml.nvmlClocksThrottleReasonHwPowerBrakeSlowdown, "Power brake"),
        (pynvml.nvmlClocksThrottleReasonHwSlowdown, "HW slowdown"),
        (pynvml.nvmlClocksThrottleReasonSyncBoost, "Sync boost"),
    ]
else:
    _THROTTLE_LABELS = []


class GPUNVMLCollector:
    """Stateful NVML collector holding a persistent device handle."""

    def __init__(self, config: NvidiaConfig | None = None) -> None:
        self.config = config or NvidiaConfig()
        self._handle = None
        self._name = "NVIDIA"
        self._nvml_inited = False  # tracks whether nvmlInit() succeeded
        self._init_failed = False
        if _NVML_AVAILABLE:
            self._init_nvml()

    def _init_nvml(self) -> None:
        try:
            pynvml.nvmlInit()
            self._nvml_inited = True
            self._handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            name = pynvml.nvmlDeviceGetName(self._handle)
            self._name = name.decode() if isinstance(name, bytes) else name
        except Exception:
            _log.debug("NVML init failed", exc_info=True)
            self._handle = None
            self._init_failed = True

    @property
    def gpu_name(self) -> str:
        return self._name

    @staticmethod
    def _try(fn, *args) -> Optional[float]:
        try:
            return fn(*args)
        except Exception:
            return None

    def collect(self) -> GPUStats:
        if self._handle is None:
            # pynvml missing or init failed — fall back to nvidia-smi parsing
            return _smi_collect(self.config)

        h = self._handle
        try:
            util = pynvml.nvmlDeviceGetUtilizationRates(h)
        except Exception:
            _log.debug("NVML utilization query failed", exc_info=True)
            return _smi_collect(self.config)

        engines: dict[str, float] = {
            "3D": float(util.gpu),
            "Memory BW": float(util.memory),
        }
        enc = self._try(pynvml.nvmlDeviceGetEncoderUtilization, h)
        if enc is not None:
            engines["Encode"] = float(enc[0])
        dec = self._try(pynvml.nvmlDeviceGetDecoderUtilization, h)
        if dec is not None:
            engines["Decode"] = float(dec[0])

        # v2 struct exposes driver-reserved memory separately; subtract it so
        # "used" matches nvidia-smi. Fall back to v1 on older drivers.
        mem = self._try(pynvml.nvmlDeviceGetMemoryInfo, h, pynvml.nvmlMemory_v2)
        reserved = getattr(mem, "reserved", 0) if mem is not None else 0
        if mem is None:
            mem = self._try(pynvml.nvmlDeviceGetMemoryInfo, h)
        power_mw = self._try(pynvml.nvmlDeviceGetPowerUsage, h)
        limit_mw = self._try(pynvml.nvmlDeviceGetEnforcedPowerLimit, h)
        temp = self._try(
            pynvml.nvmlDeviceGetTemperature, h, pynvml.NVML_TEMPERATURE_GPU
        )
        core_clk = self._try(
            pynvml.nvmlDeviceGetClockInfo, h, pynvml.NVML_CLOCK_GRAPHICS
        )
        mem_clk = self._try(pynvml.nvmlDeviceGetClockInfo, h, pynvml.NVML_CLOCK_MEM)
        fan = self._try(pynvml.nvmlDeviceGetFanSpeed, h)
        pcie_gen = self._try(pynvml.nvmlDeviceGetCurrPcieLinkGeneration, h)
        pcie_width = self._try(pynvml.nvmlDeviceGetCurrPcieLinkWidth, h)
        # KB/s — NVML returns a driver-maintained moving average (KB/s),
        # not a cumulative counter.  See nvmlDeviceGetPcieThroughput docs.
        tx_kb = self._try(
            pynvml.nvmlDeviceGetPcieThroughput, h, pynvml.NVML_PCIE_UTIL_TX_BYTES
        )
        rx_kb = self._try(
            pynvml.nvmlDeviceGetPcieThroughput, h, pynvml.NVML_PCIE_UTIL_RX_BYTES
        )

        throttle: list[str] = []
        mask = self._try(pynvml.nvmlDeviceGetCurrentClocksThrottleReasons, h)
        if mask:
            for bit, label in _THROTTLE_LABELS:
                if mask & bit:
                    throttle.append(label)

        return GPUStats(
            total_utilization=float(util.gpu),
            engines=engines,
            temp_c=float(temp) if temp is not None else None,
            clock_mhz=float(core_clk) if core_clk is not None else None,
            memory_clock_mhz=float(mem_clk) if mem_clk is not None else None,
            power_w=power_mw / 1000.0 if power_mw is not None else None,
            power_limit_w=limit_mw / 1000.0 if limit_mw is not None else None,
            mem_used_mb=(mem.used - reserved) / (1024 * 1024) if mem is not None else None,
            mem_total_mb=mem.total / (1024 * 1024) if mem is not None else None,
            fan_pct=float(fan) if fan is not None else None,
            pcie_gen=int(pcie_gen) if pcie_gen is not None else None,
            pcie_width=int(pcie_width) if pcie_width is not None else None,
            pcie_tx_mb_s=tx_kb / 1024.0 if tx_kb is not None else None,
            pcie_rx_mb_s=rx_kb / 1024.0 if rx_kb is not None else None,
            throttle_reasons=throttle,
            available=True,
        )

    def close(self) -> None:
        if self._nvml_inited:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
            self._nvml_inited = False
        self._handle = None
