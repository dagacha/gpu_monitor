"""
Hardware sensor data via LibreHardwareMonitor DLL (pythonnet).
Reads GPU and CPU sensors directly — no WMI service required.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from typing import Optional

_LHM_PATH = r"C:\Users\Office\LibreHardwareMonitor"

_CLR_READY = False
_computer = None


def _init_lhm() -> bool:
    global _CLR_READY, _computer
    try:
        import clr
        sys.path.insert(0, _LHM_PATH)
        clr.AddReference("LibreHardwareMonitorLib")
        from LibreHardwareMonitor.Hardware import Computer
        c = Computer()
        c.IsGpuEnabled = True
        c.IsCpuEnabled = True
        c.IsMotherboardEnabled = False
        c.Open()
        _computer = c
        _CLR_READY = True
        return True
    except Exception:
        return False


_init_lhm()


@dataclass
class CPUCoreData:
    index: int                         # 1-based (matching LHM "Core #N")
    load_pct: float = 0.0
    eff_clock_mhz: Optional[float] = None   # effective (accounting for C-states)
    base_clock_mhz: Optional[float] = None  # base/turbo clock
    power_w: Optional[float] = None


@dataclass
class HWSensorData:
    # GPU
    gpu_temp_c: Optional[float] = None
    gpu_clock_mhz: Optional[float] = None
    gpu_memory_clock_mhz: Optional[float] = None
    gpu_soc_clock_mhz: Optional[float] = None
    gpu_power_w: Optional[float] = None
    gpu_core_load_pct: Optional[float] = None
    # GPU memory (MB)
    gpu_mem_used_mb: Optional[float] = None
    gpu_mem_total_mb: Optional[float] = None
    gpu_mem_shared_mb: Optional[float] = None
    gpu_mem_shared_total_mb: Optional[float] = None
    # GPU D3D engine loads  (keyed by engine name e.g. "3D", "Copy", "Compute 0")
    d3d_loads: dict[str, float] = field(default_factory=dict)
    # CPU
    cpu_temp_c: Optional[float] = None
    cpu_power_w: Optional[float] = None
    cpu_total_load_pct: Optional[float] = None
    cpu_cores: list[CPUCoreData] = field(default_factory=list)
    # Combined
    soc_power_w: Optional[float] = None   # cpu_power_w + gpu_power_w
    available: bool = False


class HWMonitorCollector:

    def collect(self) -> HWSensorData:
        if not _CLR_READY or _computer is None:
            return HWSensorData(available=False)
        try:
            return self._read()
        except Exception:
            return HWSensorData(available=False)

    def _read(self) -> HWSensorData:
        data = HWSensorData()
        # Temporary dicts for building per-core data
        core_load: dict[int, float] = {}
        core_eff_clk: dict[int, float] = {}
        core_base_clk: dict[int, float] = {}
        core_power: dict[int, float] = {}

        for hw in _computer.Hardware:
            hw.Update()
            hw_type = str(hw.HardwareType)

            if hw_type == "GpuAmd":
                for s in hw.Sensors:
                    name = str(s.Name)
                    stype = str(s.SensorType)
                    val = s.Value
                    if val is None:
                        continue
                    val = float(str(val))
                    if stype == "Temperature":
                        data.gpu_temp_c = val
                    elif stype == "Clock":
                        if "Memory" in name:
                            data.gpu_memory_clock_mhz = val
                        elif "SoC" in name:
                            data.gpu_soc_clock_mhz = val
                        elif "Core" in name:
                            data.gpu_clock_mhz = val
                    elif stype == "Power" and "Core" in name:
                        data.gpu_power_w = val
                    elif stype == "Load":
                        if name == "GPU Core":
                            data.gpu_core_load_pct = val
                        elif name.startswith("D3D "):
                            data.d3d_loads[name[4:]] = val  # strip "D3D " prefix
                    elif stype == "SmallData":
                        if name == "GPU Memory Used":
                            data.gpu_mem_used_mb = val
                        elif name == "GPU Memory Total":
                            data.gpu_mem_total_mb = val
                        elif name == "D3D Shared Memory Used":
                            data.gpu_mem_shared_mb = val
                        elif name == "D3D Shared Memory Total":
                            data.gpu_mem_shared_total_mb = val

            elif hw_type == "Cpu":
                for s in hw.Sensors:
                    name = str(s.Name)
                    stype = str(s.SensorType)
                    val = s.Value
                    if val is None:
                        continue
                    val = float(str(val))

                    if stype == "Temperature" and "Tctl" in name:
                        data.cpu_temp_c = val
                    elif stype == "Power" and name == "Package":
                        data.cpu_power_w = val
                    elif stype == "Load":
                        if name == "CPU Total":
                            data.cpu_total_load_pct = val
                        else:
                            m = re.search(r"CPU Core #(\d+)$", name)
                            if m:
                                core_load[int(m.group(1))] = val
                    elif stype == "Clock":
                        m_eff = re.search(r"Core #(\d+) \(Effective\)", name)
                        m_base = re.search(r"^Core #(\d+)$", name)
                        if m_eff:
                            core_eff_clk[int(m_eff.group(1))] = val
                        elif m_base:
                            core_base_clk[int(m_base.group(1))] = val
                    elif stype == "Power":
                        m = re.search(r"Core #(\d+) \(SMU\)", name)
                        if m:
                            core_power[int(m.group(1))] = val

        # Build per-core list
        all_indices = sorted(
            set(core_load) | set(core_eff_clk) | set(core_base_clk) | set(core_power)
        )
        for idx in all_indices:
            data.cpu_cores.append(CPUCoreData(
                index=idx,
                load_pct=core_load.get(idx, 0.0),
                eff_clock_mhz=core_eff_clk.get(idx),
                base_clock_mhz=core_base_clk.get(idx),
                power_w=core_power.get(idx),
            ))

        # Combined SoC power
        if data.cpu_power_w is not None or data.gpu_power_w is not None:
            data.soc_power_w = (data.cpu_power_w or 0.0) + (data.gpu_power_w or 0.0)

        data.available = data.gpu_clock_mhz is not None or data.gpu_temp_c is not None
        return data
