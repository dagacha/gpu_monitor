"""
Process metrics for Apple Silicon via psutil.
Shows top memory-consuming processes.
"""
from __future__ import annotations

from common.types import ProcessInfo, ProcessStats


class ProcessMemoryCollector:
    """Collects top memory (RAM) processes using psutil.
    
    Sorts processes by RSS (resident set size) to show
    the biggest RAM consumers.
    """

    def __init__(self, max_processes: int = 12) -> None:
        self.max_processes = max_processes

    def collect(self) -> ProcessStats:
        """Collect top memory (RAM) processes.
        
        Returns:
            ProcessStats with top RAM consumers
        """
        try:
            import psutil
            
            # Get all processes with memory info
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'memory_percent']):
                try:
                    info = proc.info
                    if info['memory_info'] and info['memory_info'].rss > 0:
                        processes.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by RSS (resident set size) descending
            processes.sort(key=lambda x: x['memory_info'].rss if x.get('memory_info') else 0, reverse=True)
            
            # Convert to ProcessInfo
            process_infos = []
            for p in processes[:self.max_processes]:
                mem_bytes = p['memory_info'].rss if p.get('memory_info') else 0
                mem_mb = mem_bytes / (1024 * 1024)
                
                process_infos.append(ProcessInfo(
                    pid=p['pid'],
                    name=p['name'] or f"pid_{p['pid']}",
                    local_mb=mem_mb,
                    shared_mb=0.0,  # Not used on macOS
                    total_mb=mem_mb,
                ))
            
            return ProcessStats(
                processes=process_infos,
                available=True,
            )
            
        except ImportError:
            return ProcessStats(
                available=False,
                error="psutil not installed",
            )
        except Exception as e:
            return ProcessStats(
                available=False,
                error=str(e),
            )
