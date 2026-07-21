"""CPU temperature and package power via LibreHardwareMonitor.

Enriches the psutil-based CPUStats with sensors psutil cannot read on
Windows. Two sources, tried in order:

1. LibreHardwareMonitorLib DLL (pythonnet) — direct sensor access, but
   the kernel driver only loads when this process is elevated.
2. The running LibreHardwareMonitor app's Remote Web Server
   (http://localhost:8085/data.json by default). Works from non-admin
   processes and SSH sessions as long as the app is running on the
   machine with "Options -> Remote Web Server -> Run" enabled.

Without either source, enrichment is silently skipped.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
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
        self._http_cooldown = 0
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
        temps, power = self._read_dll()
        if not temps and power is None:
            temps, power = self._read_http()

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

    def _read_dll(self) -> tuple[dict[str, float], Optional[float]]:
        temps: dict[str, float] = {}
        power: Optional[float] = None
        if self._computer is None:
            return temps, power
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
            _log.debug("LHM DLL CPU read failed", exc_info=True)
        return temps, power

    def _read_http(self) -> tuple[dict[str, float], Optional[float]]:
        """Read CPU sensors from a running LHM app's Remote Web Server."""
        temps: dict[str, float] = {}
        power: Optional[float] = None
        if self._http_cooldown > 0:
            self._http_cooldown -= 1
            return temps, power
        try:
            with urllib.request.urlopen(self.config.LHM_URL, timeout=1) as r:
                tree = json.load(r)
            powers: list[float] = []
            self._walk_lhm_tree(tree, in_cpu=False, temps=temps, powers=powers)
            power = powers[0] if powers else None
        except Exception:
            # Server not running — back off so a stopped app doesn't cost a
            # failed connect every tick, then retry in case it starts later.
            _log.debug("LHM web server read failed", exc_info=True)
            self._http_cooldown = 30
        return temps, power

    _CELSIUS_RE = re.compile(r"^([\d.,]+)\s*°C$")
    _WATT_RE = re.compile(r"^([\d.,]+)\s*W$")

    def _walk_lhm_tree(
        self, node: dict, in_cpu: bool, temps: dict, powers: list
    ) -> None:
        """Recursively harvest CPU temperature/power leaves from data.json."""
        img = str(node.get("ImageURL", ""))
        if "cpu.png" in img:
            in_cpu = True
        if in_cpu:
            name = str(node.get("Text", ""))
            value = str(node.get("Value", ""))
            m = self._CELSIUS_RE.match(value)
            if m and "TjMax" not in name:
                v = float(m.group(1).replace(",", "."))
                if v > 0:
                    temps[name] = v
            elif name == "CPU Package":
                m = self._WATT_RE.match(value)
                if m:
                    powers.append(float(m.group(1).replace(",", ".")))
        for child in node.get("Children", []):
            self._walk_lhm_tree(child, in_cpu, temps, powers)

    def close(self) -> None:
        if self._computer is not None:
            try:
                self._computer.Close()
            except Exception:
                pass
            self._computer = None
