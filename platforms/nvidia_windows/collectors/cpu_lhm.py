"""CPU temperature and package power via LibreHardwareMonitor (pythonnet).

Enriches the psutil-based CPUStats with sensors psutil cannot read on
Windows. LHM's kernel driver only loads in an elevated process — without
admin the sensors read None and enrichment is silently skipped.
"""
from __future__ import annotations

import sys
from typing import Optional

from common.debug import get_logger
from common.types import CPUStats

from platforms.nvidia_windows.config import NvidiaConfig

_log = get_logger("nvidia_windows.cpu_lhm")

# Preference order for the headline temperature, most representative first
_TEMP_PRIORITY = ("CPU Package", "Core Average", "Core Max")


class CPULHMCollector:
    """Reads CPU temperature/power from the LibreHardwareMonitor DLL."""

    def __init__(self, config: NvidiaConfig | None = None) -> None:
        self.config = config or NvidiaConfig()
        self._computer = None
        try:
            import clr
            sys.path.insert(0, self.config.LHM_PATH)
            clr.AddReference("LibreHardwareMonitorLib")
            from LibreHardwareMonitor.Hardware import Computer
            c = Computer()
            c.IsCpuEnabled = True
            c.Open()
            self._computer = c
        except Exception:
            _log.debug("LibreHardwareMonitor init failed", exc_info=True)

    def enrich(self, cpu: CPUStats) -> CPUStats:
        """Fill temp_c / power_w on an existing CPUStats, if sensors read."""
        if self._computer is None:
            return cpu

        temps: dict[str, float] = {}
        power: Optional[float] = None
        try:
            for hw in self._computer.Hardware:
                if str(hw.HardwareType) != "Cpu":
                    continue
                hw.Update()
                for s in hw.Sensors:
                    val = s.Value
                    if val is None:
                        continue
                    name = str(s.Name)
                    stype = str(s.SensorType)
                    if stype == "Temperature" and "TjMax" not in name:
                        v = float(str(val))
                        if v > 0:
                            temps[name] = v
                    elif stype == "Power" and name == "CPU Package":
                        v = float(str(val))
                        if v > 0:
                            power = v
        except Exception:
            _log.debug("LHM CPU read failed", exc_info=True)
            return cpu

        if cpu.temp_c is None and temps:
            for needle in _TEMP_PRIORITY:
                if needle in temps:
                    cpu.temp_c = temps[needle]
                    break
            else:
                cpu.temp_c = max(temps.values())
        if cpu.power_w is None and power is not None:
            cpu.power_w = power
        return cpu

    def close(self) -> None:
        if self._computer is not None:
            try:
                self._computer.Close()
            except Exception:
                pass
            self._computer = None
