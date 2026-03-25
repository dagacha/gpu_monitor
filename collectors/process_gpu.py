"""
Per-process GPU memory usage via Windows PDH.
Refreshes the process list every REFRESH_TICKS seconds.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

try:
    import win32pdh
    _PDH_AVAILABLE = True
except ImportError:
    _PDH_AVAILABLE = False

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

REFRESH_TICKS = 5


@dataclass
class ProcessGPUStat:
    pid: int
    name: str
    local_bytes: int    # GPU-local (dedicated) memory
    shared_bytes: int   # Shared system RAM used by GPU

    @property
    def total_bytes(self) -> int:
        return self.local_bytes + self.shared_bytes


def _enumerate_instances(obj: str) -> list[str]:
    try:
        _, instances = win32pdh.EnumObjectItems(
            None, None, obj, win32pdh.PERF_DETAIL_WIZARD
        )
        return instances or []
    except Exception:
        return []


def _read_handle(handle, fmt=None) -> int:
    if fmt is None:
        fmt = win32pdh.PDH_FMT_LARGE
    try:
        _, val = win32pdh.GetFormattedCounterValue(handle, fmt)
        return int(val)
    except Exception:
        return 0


class ProcessGPUCollector:
    """Tracks per-process GPU memory, refreshed every REFRESH_TICKS seconds."""

    def __init__(self) -> None:
        self._query = None
        # pid -> {'local': [handles...], 'shared': [handles...]}
        self._pid_handles: dict[int, dict[str, list]] = {}
        self._ticks = REFRESH_TICKS  # trigger rebuild on first collect()
        self._last: list[ProcessGPUStat] = []

    def _rebuild(self) -> None:
        if not _PDH_AVAILABLE:
            return
        # Close old query
        if self._query is not None:
            try:
                win32pdh.CloseQuery(self._query)
            except Exception:
                pass
        self._query = None
        self._pid_handles = {}

        try:
            query = win32pdh.OpenQuery()
            instances = _enumerate_instances("GPU Process Memory")

            # Group instances by PID
            pid_insts: dict[int, list[str]] = {}
            for inst in instances:
                m = re.match(r"pid_(\d+)_", inst)
                if m:
                    pid = int(m.group(1))
                    pid_insts.setdefault(pid, []).append(inst)

            for pid, insts in pid_insts.items():
                local_hs, shared_hs = [], []
                for inst in insts:
                    try:
                        lh = win32pdh.AddCounter(
                            query, f"\\GPU Process Memory({inst})\\Local Usage"
                        )
                        local_hs.append(lh)
                    except Exception:
                        pass
                    try:
                        sh = win32pdh.AddCounter(
                            query, f"\\GPU Process Memory({inst})\\Shared Usage"
                        )
                        shared_hs.append(sh)
                    except Exception:
                        pass
                if local_hs or shared_hs:
                    self._pid_handles[pid] = {"local": local_hs, "shared": shared_hs}

            # Single sample — these are instantaneous byte counters, not rates
            win32pdh.CollectQueryData(query)
            self._query = query
        except Exception:
            self._query = None

    def collect(self) -> list[ProcessGPUStat]:
        if not _PDH_AVAILABLE:
            return []

        self._ticks += 1
        if self._ticks >= REFRESH_TICKS:
            self._ticks = 0
            self._rebuild()
        elif self._query is not None:
            try:
                win32pdh.CollectQueryData(self._query)
            except Exception:
                self._rebuild()
                return self._last

        if self._query is None:
            return self._last

        results: list[ProcessGPUStat] = []
        for pid, handles in self._pid_handles.items():
            local = sum(_read_handle(h) for h in handles["local"])
            shared = sum(_read_handle(h) for h in handles["shared"])
            if local == 0 and shared == 0:
                continue
            if _PSUTIL_AVAILABLE:
                try:
                    name = psutil.Process(pid).name()
                except Exception:
                    name = f"pid_{pid}"
            else:
                name = f"pid_{pid}"
            results.append(ProcessGPUStat(pid, name, local, shared))

        results.sort(key=lambda x: x.total_bytes, reverse=True)
        self._last = results[:20]
        return self._last

    def close(self) -> None:
        if self._query is not None:
            try:
                win32pdh.CloseQuery(self._query)
            except Exception:
                pass
            self._query = None
