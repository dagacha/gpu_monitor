"""
Process metrics for Apple Silicon via psutil.
Shows top CPU-consuming processes (no GPU data available on macOS).
"""
from __future__ import annotations

from common.types import ProcessInfo, ProcessStats


class ProcessCollector:
    """Collects top CPU processes using psutil.
    
    Note: macOS has no public API for per-process GPU memory/usage.
    This shows CPU processes instead.
    """

    def __init__(self, max_processes: int = 12) -> None:
        self.max_processes = max_processes

    def collect(self) -> ProcessStats:
        """Collect top CPU processes.
        
        Returns:
            ProcessStats with top CPU consumers
        """
        try:
            import psutil
            
            # Get all processes with CPU percent
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    info = proc.info
                    if info['cpu_percent'] and info['cpu_percent'] > 0.1:  # Filter idle processes
                        processes.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by CPU percent descending
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            
            # Convert to ProcessInfo
            process_infos = []
            for p in processes[:self.max_processes]:
                # Estimate "memory" as a placeholder (psutil doesn't give GPU mem on macOS)
                # Use rss as a proxy
                try:
                    proc = psutil.Process(p['pid'])
                    mem_mb = proc.memory_info().rss / (1024 * 1024)
                except:
                    mem_mb = 0.0
                
                process_infos.append(ProcessInfo(
                    pid=p['pid'],
                    name=p['name'] or f"pid_{p['pid']}",
                    local_mb=mem_mb,  # Using RSS as a stand-in
                    shared_mb=0.0,     # Not available on macOS
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
