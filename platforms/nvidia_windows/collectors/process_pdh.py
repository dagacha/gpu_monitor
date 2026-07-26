r"""Per-process GPU memory and utilization via Windows PDH.

Reads \GPU Process Memory(pid_*)\Local/Shared Usage and
\GPU Engine(pid_*)\Utilization Percentage — the same counters Task Manager
uses. Works without admin and covers graphics (WDDM) processes that
nvidia-smi --query-compute-apps cannot see.

Falls back to the nvidia-smi collector when pywin32 is unavailable.
"""
from __future__ import annotations

import re

from common.debug import get_logger
from common.types import ProcessInfo, ProcessStats

from platforms.nvidia_windows.config import NvidiaConfig
from platforms.nvidia_windows.collectors.process import collect as _smi_collect

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

_log = get_logger("nvidia_windows.process_pdh")

# Re-enumerate PDH instances every N ticks to pick up new/exited processes
REFRESH_TICKS = 5

_PID_RE = re.compile(r"pid_(\d+)_")


def _enumerate_instances(obj: str) -> list[str]:
    try:
        _, instances = win32pdh.EnumObjectItems(
            None, None, obj, win32pdh.PERF_DETAIL_WIZARD
        )
        return instances or []
    except Exception:
        return []


def _read_large(handle) -> int:
    try:
        _, val = win32pdh.GetFormattedCounterValue(handle, win32pdh.PDH_FMT_LARGE)
        return int(val)
    except Exception:
        return 0


def _read_double(handle) -> float:
    try:
        _, val = win32pdh.GetFormattedCounterValue(handle, win32pdh.PDH_FMT_DOUBLE)
        return float(val)
    except Exception:
        return 0.0


class ProcessPDHCollector:
    """Per-process GPU memory + engine utilization, top consumers by VRAM."""

    def __init__(self, config: NvidiaConfig | None = None) -> None:
        self.config = config or NvidiaConfig()
        self._query = None
        # pid -> {'local': [...], 'shared': [...], 'engine': [...]} counter handles
        self._pid_handles: dict[int, dict[str, list]] = {}
        self._ticks = REFRESH_TICKS  # trigger rebuild on first collect()
        self._last = ProcessStats(available=False)

    def _rebuild(self) -> None:
        self.close()
        self._pid_handles = {}
        try:
            query = win32pdh.OpenQuery()

            for inst in _enumerate_instances("GPU Process Memory"):
                m = _PID_RE.match(inst)
                if not m:
                    continue
                pid = int(m.group(1))
                entry = self._pid_handles.setdefault(
                    pid, {"local": [], "shared": [], "engine": []}
                )
                for counter, key in (("Local Usage", "local"), ("Shared Usage", "shared")):
                    try:
                        h = win32pdh.AddCounter(
                            query, f"\\GPU Process Memory({inst})\\{counter}"
                        )
                        entry[key].append(h)
                    except Exception:
                        pass

            for inst in _enumerate_instances("GPU Engine"):
                m = _PID_RE.match(inst)
                if not m:
                    continue
                pid = int(m.group(1))
                entry = self._pid_handles.setdefault(
                    pid, {"local": [], "shared": [], "engine": []}
                )
                try:
                    h = win32pdh.AddCounter(
                        query, f"\\GPU Engine({inst})\\Utilization Percentage"
                    )
                    entry["engine"].append(h)
                except Exception:
                    pass

            # Baseline sample — engine counters are rates and need two samples
            win32pdh.CollectQueryData(query)
            self._query = query
        except Exception:
            _log.debug("PDH rebuild failed", exc_info=True)
            self._query = None

    def collect(self) -> ProcessStats:
        if not _PDH_AVAILABLE:
            return _smi_collect(self.config)

        self._ticks += 1
        if self._ticks >= REFRESH_TICKS:
            self._ticks = 0
            self._rebuild()
            # Engine counters need two samples. The rebuild's baseline
            # CollectQueryData is the first; fall through to collect a
            # second sample below so the first tick returns real data
            # instead of available=False.

        if self._query is not None:
            try:
                win32pdh.CollectQueryData(self._query)
            except Exception:
                self._rebuild()
                return self._last

        if self._query is None:
            return self._last

        processes: list[ProcessInfo] = []
        for pid, handles in self._pid_handles.items():
            local = sum(_read_large(h) for h in handles["local"])
            shared = sum(_read_large(h) for h in handles["shared"])
            util = min(sum(_read_double(h) for h in handles["engine"]), 100.0)
            if local == 0 and shared == 0 and util == 0:
                continue
            if _PSUTIL_AVAILABLE:
                try:
                    name = psutil.Process(pid).name()
                except Exception:
                    name = f"pid_{pid}"
            else:
                name = f"pid_{pid}"
            processes.append(ProcessInfo(
                pid=pid,
                name=name,
                local_mb=local / (1024 * 1024),
                shared_mb=shared / (1024 * 1024),
                total_mb=(local + shared) / (1024 * 1024),
                gpu_util_pct=util,
            ))

        processes.sort(key=lambda p: p.total_mb, reverse=True)
        self._last = ProcessStats(processes=processes[:20], available=True)
        return self._last

    def close(self) -> None:
        if self._query is not None:
            try:
                win32pdh.CloseQuery(self._query)
            except Exception:
                pass
            self._query = None
