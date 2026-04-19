"""
Hardware sensor data via LibreHardwareMonitor DLL (pythonnet).
Reads GPU and CPU sensors directly — no WMI service required.
Returns common.types.CPUStats and enriches GPU/power data.
"""
from __future__ import annotations

import re
import sys
from typing import Optional

from common.types import CPUCoreData, CPUStats, GPUStats, PowerStats
from platforms.amd_ryzen.config import AMDConfig

_CLR_READY = False
_computer = None


def _init_lhm() -> bool:
    global _CLR_READY, _computer
    try:
        import clr
        sys.path.insert(0, AMDConfig.LHM_PATH)
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


class HWMonitorCollector:
    """Collects CPU and sensor data via LibreHardwareMonitor.
    
    Returns common.types.CPUStats and provides helper methods to enrich
    GPUStats and PowerStats from the same data source.
    """

    def __init__(self) -> None:
        self._d3d_loads: dict[str, float] = {}

    def collect(self) -> CPUStats:
        if not _CLR_READY or _computer is None:
            return CPUStats(available=False, error="LHM not available")
        try:
            return self._read_cpu()
        except Exception as e:
            return CPUStats(available=False, error=str(e))

    def _read_cpu(self) -> CPUStats:
        """Read CPU-specific data from LHM."""
        cores_data: dict[int, CPUCoreData] = {}
        cpu_temp: Optional[float] = None
        cpu_power: Optional[float] = None
        cpu_total_load: Optional[float] = None

        for hw in _computer.Hardware:
            hw.Update()
            hw_type = str(hw.HardwareType)

            if hw_type == "Cpu":
                for s in hw.Sensors:
                    name = str(s.Name)
                    stype = str(s.SensorType)
                    val = s.Value
                    if val is None:
                        continue
                    val = float(str(val))

                    if stype == "Temperature" and "Tctl" in name:
                        cpu_temp = val
                    elif stype == "Power" and name == "Package":
                        cpu_power = val
                    elif stype == "Load":
                        if name == "CPU Total":
                            cpu_total_load = val
                        else:
                            m = re.search(r"CPU Core #(\d+)$", name)
                            if m:
                                idx = int(m.group(1))
                                if idx not in cores_data:
                                    cores_data[idx] = CPUCoreData(index=idx)
                                cores_data[idx].load_pct = val
                    elif stype == "Clock":
                        m_eff = re.search(r"Core #(\d+) \(Effective\)", name)
                        if m_eff:
                            idx = int(m_eff.group(1))
                            if idx not in cores_data:
                                cores_data[idx] = CPUCoreData(index=idx)
                            cores_data[idx].eff_clock_mhz = val
                    elif stype == "Power":
                        m = re.search(r"Core #(\d+) \(SMU\)", name)
                        if m:
                            idx = int(m.group(1))
                            if idx not in cores_data:
                                cores_data[idx] = CPUCoreData(index=idx)
                            cores_data[idx].power_w = val

        cores = [cores_data[idx] for idx in sorted(cores_data.keys())]
        available = cpu_temp is not None or cpu_total_load is not None or len(cores) > 0

        return CPUStats(
            temp_c=cpu_temp,
            total_load_pct=cpu_total_load,
            cores=cores,
            power_w=cpu_power,
            available=available,
        )

    def enrich_gpu(self, gpu: GPUStats) -> GPUStats:
        """Enrich GPUStats with LHM data (temp, clocks, power, memory)."""
        if not _CLR_READY or _computer is None:
            return gpu

        try:
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
                            gpu.temp_c = val
                        elif stype == "Clock":
                            if "Memory" in name:
                                gpu.memory_clock_mhz = val
                            elif "SoC" in name:
                                pass  # We don't track SoC clock in shared type
                            elif "Core" in name:
                                gpu.clock_mhz = val
                        elif stype == "Power" and "Core" in name:
                            gpu.power_w = val
                        elif stype == "Load":
                            if name == "GPU Core":
                                # Prefer LHM core load over PDH if available
                                pass
                            elif name.startswith("D3D "):
                                self._d3d_loads[name[4:]] = val
                        elif stype == "SmallData":
                            if name == "GPU Memory Used":
                                gpu.mem_used_mb = val
                            elif name == "GPU Memory Total":
                                gpu.mem_total_mb = val
                            elif name == "D3D Shared Memory Used":
                                gpu.mem_shared_mb = val
                            elif name == "D3D Shared Memory Total":
                                gpu.mem_shared_total_mb = val

            # Merge D3D loads into engines
            if self._d3d_loads:
                for name, load in self._d3d_loads.items():
                    if name not in gpu.engines:
                        gpu.engines[name] = load

        except Exception:
            pass

        return gpu

    def enrich_power(self, power: PowerStats) -> PowerStats:
        """Enrich PowerStats with LHM data (CPU/GPU power, SoC total)."""
        if not _CLR_READY or _computer is None:
            return power

        try:
            cpu_power: Optional[float] = None
            gpu_power: Optional[float] = None

            for hw in _computer.Hardware:
                hw.Update()
                hw_type = str(hw.HardwareType)

                if hw_type == "Cpu":
                    for s in hw.Sensors:
                        name = str(s.Name)
                        stype = str(s.SensorType)
                        val = s.Value
                        if val is None:
                            continue
                        if stype == "Power" and name == "Package":
                            cpu_power = float(str(val))

                elif hw_type == "GpuAmd":
                    for s in hw.Sensors:
                        name = str(s.Name)
                        stype = str(s.SensorType)
                        val = s.Value
                        if val is None:
                            continue
                        if stype == "Power" and "Core" in name:
                            gpu_power = float(str(val))

            if cpu_power is not None:
                power.cpu_power_w = cpu_power
            if gpu_power is not None:
                power.gpu_power_w = gpu_power
            if cpu_power is not None or gpu_power is not None:
                power.soc_power_w = (cpu_power or 0.0) + (gpu_power or 0.0)
                power.package_power_w = power.soc_power_w

        except Exception:
            pass

        return power
