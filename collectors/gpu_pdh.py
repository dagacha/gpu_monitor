r"""
GPU utilization and memory via Windows Performance Data Helper (PDH).
Reads \GPU Engine(*)\Utilization Percentage and \GPU Process Memory(*) counters.
Requires pywin32.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

try:
    import win32pdh
    _PDH_AVAILABLE = True
except ImportError:
    _PDH_AVAILABLE = False


@dataclass
class GPUEngineStats:
    name: str          # e.g. "3D", "Compute", "Video"
    utilization: float # 0.0 – 100.0

@dataclass
class GPUStats:
    engines: list[GPUEngineStats] = field(default_factory=list)
    total_utilization: float = 0.0
    local_memory_bytes: int = 0
    shared_memory_bytes: int = 0
    available: bool = False


# Rebuild the PDH query every N ticks to pick up new GPU processes
_REENUMERATE_INTERVAL = 10


class GPUPDHCollector:
    """Collects GPU counters using the Windows PDH API."""

    def __init__(self) -> None:
        self._query = None
        self._engine_counters: dict[str, list] = {}
        self._local_mem_handles: list = []
        self._shared_mem_handles: list = []
        self._ready = False
        self._ticks_since_rebuild = 0

        if _PDH_AVAILABLE:
            self._setup()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup(self) -> None:
        try:
            self._query = win32pdh.OpenQuery()

            # --- Enumerate GPU Engine instances ---
            engine_instances = self._enumerate_instances("GPU Engine")
            for instance in engine_instances:
                engtype = self._extract_engtype(instance)
                if engtype is None:
                    continue
                counter_path = f"\\GPU Engine({instance})\\Utilization Percentage"
                try:
                    handle = win32pdh.AddCounter(self._query, counter_path)
                    self._engine_counters.setdefault(engtype, []).append(handle)
                except Exception:
                    pass

            # --- Enumerate GPU Process Memory instances ---
            local_handles = []
            shared_handles = []
            for instance in self._enumerate_instances("GPU Process Memory"):
                try:
                    h = win32pdh.AddCounter(
                        self._query, f"\\GPU Process Memory({instance})\\Local Usage"
                    )
                    local_handles.append(h)
                except Exception:
                    pass
                try:
                    h = win32pdh.AddCounter(
                        self._query, f"\\GPU Process Memory({instance})\\Shared Usage"
                    )
                    shared_handles.append(h)
                except Exception:
                    pass

            self._local_mem_handles = local_handles
            self._shared_mem_handles = shared_handles

            # Prime the counters — PDH needs one baseline sample before rates are valid.
            # The first collect() call after this will have the second sample and valid rates.
            win32pdh.CollectQueryData(self._query)
            self._ready = bool(self._engine_counters)
        except Exception:
            self._ready = False

    @staticmethod
    def _enumerate_instances(object_name: str) -> list[str]:
        try:
            _, instances = win32pdh.EnumObjectItems(
                None, None, object_name, win32pdh.PERF_DETAIL_WIZARD
            )
            return instances or []
        except Exception:
            return []

    @staticmethod
    def _extract_engtype(instance: str) -> Optional[str]:
        m = re.search(r"engtype_(\w+)", instance, re.IGNORECASE)
        return m.group(1) if m else None

    def _rebuild(self) -> None:
        self.close()
        self._engine_counters = {}
        self._local_mem_handles = []
        self._shared_mem_handles = []
        self._ready = False
        self._setup()

    # ------------------------------------------------------------------
    # Collection
    # ------------------------------------------------------------------

    def collect(self) -> GPUStats:
        if not _PDH_AVAILABLE:
            return GPUStats(available=False)

        # Periodically re-enumerate instances so new GPU processes are counted
        self._ticks_since_rebuild += 1
        if self._ticks_since_rebuild >= _REENUMERATE_INTERVAL:
            self._ticks_since_rebuild = 0
            self._rebuild()

        if not self._ready:
            return GPUStats(available=False)

        try:
            win32pdh.CollectQueryData(self._query)
        except Exception:
            self._rebuild()
            return GPUStats(available=False)

        engines: list[GPUEngineStats] = []
        for engtype, handles in self._engine_counters.items():
            total = 0.0
            for handle in handles:
                try:
                    _, val = win32pdh.GetFormattedCounterValue(
                        handle, win32pdh.PDH_FMT_DOUBLE
                    )
                    total += val
                except Exception:
                    pass
            engines.append(GPUEngineStats(name=engtype, utilization=min(total, 100.0)))

        engines.sort(key=lambda e: e.name)

        return GPUStats(
            engines=engines,
            total_utilization=max((e.utilization for e in engines), default=0.0),
            local_memory_bytes=self._sum_handles(self._local_mem_handles),
            shared_memory_bytes=self._sum_handles(self._shared_mem_handles),
            available=True,
        )

    def _sum_handles(self, handles: list) -> int:
        total = 0
        for h in handles:
            try:
                _, val = win32pdh.GetFormattedCounterValue(h, win32pdh.PDH_FMT_LARGE)
                total += int(val)
            except Exception:
                pass
        return total

    def close(self) -> None:
        if self._query is not None:
            try:
                win32pdh.CloseQuery(self._query)
            except Exception:
                pass
            self._query = None
