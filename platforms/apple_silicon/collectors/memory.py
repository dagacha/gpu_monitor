"""
Memory metrics for Apple Silicon via psutil and vm_stat.
No sudo required. Shows unified memory breakdown.
"""
from __future__ import annotations

import re
import subprocess
from typing import Optional

from common.types import MemoryRow, MemoryStats


def _vm_stat() -> dict[str, int]:
    """Parse vm_stat output into a dictionary."""
    result = {}
    try:
        r = subprocess.run(
            ["vm_stat"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if r.returncode == 0:
            # Parse lines like "Pages free:                              188993."
            for line in r.stdout.splitlines():
                match = re.match(r"^(Pages \w+):\s+(\d+)\.$", line)
                if match:
                    key = match.group(1).lower().replace(" ", "_")
                    result[key] = int(match.group(2))
    except Exception:
        pass
    return result


def _get_page_size() -> int:
    """Get system page size."""
    try:
        result = subprocess.run(
            ["sysctl", "-n", "vm.pagesize"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except Exception:
        pass
    return 16384  # Default for Apple Silicon


class MemoryCollector:
    """Collects memory metrics for Apple Silicon.
    
    Uses psutil for high-level stats and vm_stat for detailed breakdown.
    No sudo required.
    """

    def __init__(self) -> None:
        self._page_size: int | None = None

    def _get_page_size(self) -> int:
        """Get or cache page size."""
        if self._page_size is None:
            self._page_size = _get_page_size()
        return self._page_size

    def _pages_to_mb(self, pages: int) -> float:
        """Convert pages to megabytes."""
        return (pages * self._get_page_size()) / (1024 * 1024)

    def collect(self) -> MemoryStats:
        """Collect memory stats from psutil and vm_stat."""
        try:
            import psutil
            
            vm = psutil.virtual_memory()
            vm_data = _vm_stat()
            
            rows: list[MemoryRow] = []
            
            # Physical memory
            total_mb = vm.total / (1024 * 1024)
            used_mb = vm.used / (1024 * 1024)
            pct = vm.percent
            
            rows.append(MemoryRow(
                label="System RAM",
                used_mb=used_mb,
                total_mb=total_mb,
                pct=pct,
            ))
            
            # Detailed breakdown from vm_stat (if available)
            if vm_data:
                # Wired memory (kernel, drivers, locked)
                if "pages_wired_down" in vm_data:
                    wired_mb = self._pages_to_mb(vm_data["pages_wired_down"])
                    rows.append(MemoryRow(
                        label="  └ Wired",
                        used_mb=wired_mb,
                        total_mb=None,  # Sub-item, no total
                        pct=(wired_mb / total_mb * 100) if total_mb > 0 else 0,
                    ))
                
                # Active memory
                if "pages_active" in vm_data:
                    active_mb = self._pages_to_mb(vm_data["pages_active"])
                    rows.append(MemoryRow(
                        label="  └ Active",
                        used_mb=active_mb,
                        total_mb=None,
                        pct=(active_mb / total_mb * 100) if total_mb > 0 else 0,
                    ))
                
                # Inactive memory
                if "pages_inactive" in vm_data:
                    inactive_mb = self._pages_to_mb(vm_data["pages_inactive"])
                    rows.append(MemoryRow(
                        label="  └ Inactive",
                        used_mb=inactive_mb,
                        total_mb=None,
                        pct=(inactive_mb / total_mb * 100) if total_mb > 0 else 0,
                    ))
                
                # Free memory
                if "pages_free" in vm_data:
                    free_mb = self._pages_to_mb(vm_data["pages_free"])
                    rows.append(MemoryRow(
                        label="  └ Free",
                        used_mb=free_mb,
                        total_mb=None,
                        pct=(free_mb / total_mb * 100) if total_mb > 0 else 0,
                    ))
                
                # Compressor (memory pressure indicator)
                if "pages_used_by_compressor" in vm_data:
                    compressed_mb = self._pages_to_mb(vm_data["pages_used_by_compressor"])
                    if compressed_mb > 0:
                        rows.append(MemoryRow(
                            label="  └ Compressed",
                            used_mb=compressed_mb,
                            total_mb=None,
                            pct=(compressed_mb / total_mb * 100) if total_mb > 0 else 0,
                        ))
            
            return MemoryStats(
                rows=rows,
                available=True,
            )
            
        except ImportError:
            return MemoryStats(available=False, error="psutil not installed")
        except Exception as e:
            return MemoryStats(available=False, error=str(e))
