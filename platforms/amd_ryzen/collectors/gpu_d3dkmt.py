"""
GPU temperature / power / clocks via the Windows WDDM kernel API.

Uses gdi32's D3DKMT* exports with KMTQAITYPE_ADAPTERPERFDATA — the same data
source Task Manager's GPU page uses. This works for adapters (including iGPUs
like the Radeon 8060S on Strix Halo) that LibreHardwareMonitor does not expose
temperature sensors for.

References:
    https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/d3dkmthk/ns-d3dkmthk-_d3dkmt_adapter_perfdata
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Optional

# KMTQUERYADAPTERINFOTYPE has been renumbered across Windows SDKs; on
# Windows 11 26200 the ADAPTERPERFDATA type that accepts the 64-byte
# _D3DKMT_ADAPTER_PERFDATA struct is value 62. Determined empirically by
# scanning the enum on the target machine.
_KMTQAITYPE_ADAPTERPERFDATA = 62

# DISPLAY_DEVICE.StateFlags
_DISPLAY_DEVICE_ATTACHED_TO_DESKTOP = 0x00000001


class _LUID(ctypes.Structure):
    _fields_ = [
        ("LowPart", wintypes.DWORD),
        ("HighPart", wintypes.LONG),
    ]


class _D3DKMT_OPENADAPTERFROMGDIDISPLAYNAME(ctypes.Structure):
    _fields_ = [
        ("DeviceName", wintypes.WCHAR * 32),
        ("hAdapter", wintypes.UINT),
        ("AdapterLuid", _LUID),
        ("VidPnSourceId", wintypes.UINT),
    ]


class _D3DKMT_QUERYADAPTERINFO(ctypes.Structure):
    _fields_ = [
        ("hAdapter", wintypes.UINT),
        ("Type", ctypes.c_int),
        ("pPrivateDriverData", ctypes.c_void_p),
        ("PrivateDriverDataSize", ctypes.c_uint),
    ]


class _D3DKMT_ADAPTER_PERFDATA(ctypes.Structure):
    _fields_ = [
        ("PhysicalAdapterIndex", ctypes.c_uint),
        ("MemoryFrequency", ctypes.c_ulonglong),
        ("MaxMemoryFrequency", ctypes.c_ulonglong),
        ("MaxMemoryFrequencyOC", ctypes.c_ulonglong),
        ("MemoryBandwidth", ctypes.c_ulonglong),
        ("PCIEBandwidth", ctypes.c_ulonglong),
        ("FanRPM", ctypes.c_uint),
        ("Power", ctypes.c_uint),         # milli-percent of TDP (0..100000)
        ("Temperature", ctypes.c_uint),   # deci-Celsius
        ("PowerStateOverride", ctypes.c_ubyte),
    ]


class _D3DKMT_CLOSEADAPTER(ctypes.Structure):
    _fields_ = [("hAdapter", wintypes.UINT)]


class _DISPLAY_DEVICEW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("DeviceName", wintypes.WCHAR * 32),
        ("DeviceString", wintypes.WCHAR * 128),
        ("StateFlags", wintypes.DWORD),
        ("DeviceID", wintypes.WCHAR * 128),
        ("DeviceKey", wintypes.WCHAR * 128),
    ]


try:
    _gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _D3DKMT_AVAILABLE = True
except OSError:
    _gdi32 = None
    _user32 = None
    _D3DKMT_AVAILABLE = False


class GPUPerfData:
    """Result bundle from a single D3DKMT query."""

    __slots__ = (
        "temp_c",
        "power_pct",
        "core_clock_mhz",
        "memory_clock_mhz",
        "memory_clock_max_mhz",
        "fan_rpm",
        "adapter_name",
    )

    def __init__(
        self,
        temp_c: Optional[float] = None,
        power_pct: Optional[float] = None,
        core_clock_mhz: Optional[float] = None,
        memory_clock_mhz: Optional[float] = None,
        memory_clock_max_mhz: Optional[float] = None,
        fan_rpm: Optional[int] = None,
        adapter_name: str = "",
    ) -> None:
        self.temp_c = temp_c
        self.power_pct = power_pct
        self.core_clock_mhz = core_clock_mhz
        self.memory_clock_mhz = memory_clock_mhz
        self.memory_clock_max_mhz = memory_clock_max_mhz
        self.fan_rpm = fan_rpm
        self.adapter_name = adapter_name


class GPUD3DKMTCollector:
    """Reads GPU perf data from the WDDM kernel via gdi32.

    Caches an opened adapter handle keyed by display device name. If the
    underlying adapter changes (e.g., display reconfigured) the handle is
    closed and reopened on the next failure.
    """

    def __init__(self) -> None:
        self._adapter_handle: Optional[int] = None
        self._adapter_name: str = ""
        self._adapter_device: str = ""
        self._failed = not _D3DKMT_AVAILABLE

    # ------------------------------------------------------------------

    def available(self) -> bool:
        return _D3DKMT_AVAILABLE and not self._failed

    def collect(self) -> Optional[GPUPerfData]:
        if not _D3DKMT_AVAILABLE:
            return None

        if self._adapter_handle is None and not self._open_adapter():
            return None

        try:
            perf = _D3DKMT_ADAPTER_PERFDATA()
            q = _D3DKMT_QUERYADAPTERINFO()
            q.hAdapter = self._adapter_handle
            q.Type = _KMTQAITYPE_ADAPTERPERFDATA
            q.pPrivateDriverData = ctypes.cast(
                ctypes.byref(perf), ctypes.c_void_p
            ).value
            q.PrivateDriverDataSize = ctypes.sizeof(perf)

            status = _gdi32.D3DKMTQueryAdapterInfo(ctypes.byref(q))
            if status != 0:
                # NTSTATUS != STATUS_SUCCESS — adapter may have gone away.
                self._close_adapter()
                return None

            temp_c = perf.Temperature / 10.0 if perf.Temperature else None
            power_pct = perf.Power / 1000.0 if perf.Power else None  # 0..100
            mem_mhz = perf.MemoryFrequency / 1_000_000.0 if perf.MemoryFrequency else None
            mem_max_mhz = (
                perf.MaxMemoryFrequency / 1_000_000.0
                if perf.MaxMemoryFrequency else None
            )

            return GPUPerfData(
                temp_c=temp_c,
                power_pct=power_pct,
                core_clock_mhz=None,  # not in ADAPTERPERFDATA on most drivers
                memory_clock_mhz=mem_mhz,
                memory_clock_max_mhz=mem_max_mhz,
                fan_rpm=perf.FanRPM or None,
                adapter_name=self._adapter_name,
            )
        except Exception:
            self._close_adapter()
            return None

    def close(self) -> None:
        self._close_adapter()

    # ------------------------------------------------------------------

    def _open_adapter(self) -> bool:
        """Find the first display-attached adapter and open it."""
        if not _D3DKMT_AVAILABLE:
            return False

        device = _DISPLAY_DEVICEW()
        device.cb = ctypes.sizeof(device)

        i = 0
        while _user32.EnumDisplayDevicesW(None, i, ctypes.byref(device), 0):
            i += 1
            if not (device.StateFlags & _DISPLAY_DEVICE_ATTACHED_TO_DESKTOP):
                continue

            opener = _D3DKMT_OPENADAPTERFROMGDIDISPLAYNAME()
            opener.DeviceName = device.DeviceName
            status = _gdi32.D3DKMTOpenAdapterFromGdiDisplayName(
                ctypes.byref(opener)
            )
            if status == 0:
                self._adapter_handle = opener.hAdapter
                self._adapter_name = device.DeviceString
                self._adapter_device = device.DeviceName
                return True

            # reset for next iter
            device = _DISPLAY_DEVICEW()
            device.cb = ctypes.sizeof(device)

        self._failed = True  # nothing usable on this machine
        return False

    def _close_adapter(self) -> None:
        if self._adapter_handle is not None and _gdi32 is not None:
            try:
                close = _D3DKMT_CLOSEADAPTER()
                close.hAdapter = self._adapter_handle
                _gdi32.D3DKMTCloseAdapter(ctypes.byref(close))
            except Exception:
                pass
        self._adapter_handle = None
