# gpu_monitor

An htop-like terminal GPU/CPU/NPU monitor for **AMD Ryzen AI Max** (Windows), **Apple Silicon** (macOS), and **NVIDIA GPUs** (Linux).

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)

## Supported Platforms

| Platform | GPU | CPU | Memory | NPU | Power/Thermal |
|----------|-----|-----|--------|-----|---------------|
| **AMD Ryzen AI Max** (Windows 11) | ✅ Radeon 8060S | ✅ Per-core | ✅ UMA | ✅ XDNA | ✅ SoC |
| **Apple Silicon** (macOS) | ✅ M1/M2/M3/M4 | ✅ Per-core | ✅ Unified | ❌ Not exposed | ✅ Thermal |
| **NVIDIA GPU** (Linux) | ✅ RTX/GTX | ✅ Per-core | ✅ System | ❌ Not exposed | ✅ Power |


## What it shows

### AMD Ryzen (Windows)

| Panel | Metrics |
|-------|---------|
| **GPU** | Per-engine utilization (3D / Compute / Copy / Video), 60s sparkline, temperature, clocks, power |
| **NPU** | XDNA partitions, HW contexts, GOPS, XRT / firmware versions (via `xrt-smi`) |
| **Memory** | GPU dedicated, GPU shared, system RAM — all from unified memory pool |
| **Processes** | Top GPU memory consumers (local + shared), refreshed every 5s |
| **CPU** | Per-core load bars + effective clock (GHz), package temperature and power |
| **Power** | Combined CPU + GPU power draw |

### Apple Silicon (macOS)

| Panel | Metrics |
|-------|---------|
| **GPU** | Active %, frequency, power — requires `sudo` for powermetrics |
| **Memory** | Unified memory breakdown: wired, active, inactive, free, compressed |
| **CPU** | Per-core load bars, frequency from powermetrics (with sudo) |
| **Power** | CPU/GPU power draw, thermal pressure level (Nominal/Fair/Serious/Critical) |

### NVIDIA (Linux)

| Panel | Metrics |
|-------|---------|
| **GPU** | Utilization, Memory usage, Temperature, Power draw, Clock speeds |
| **Memory** | System RAM utilization |
| **CPU** | Per-core load bars |
| **Power** | GPU Power draw (Watts) |

## Quick Start

### AMD Ryzen (Windows 11)

```bat
git clone https://github.com/dagacha/gpu_monitor.git
cd gpu_monitor
pip install -r requirements.txt
python main.py
```

### Apple Silicon (macOS)

```bash
git clone https://github.com/dagacha/gpu_monitor.git
cd gpu_monitor
pip install -r requirements.txt

# Basic (CPU + memory)
python main.py

# Full features (GPU + power + thermal) — requires sudo
sudo python main.py
```

### NVIDIA (Linux)

```bash
git clone https://github.com/dagacha/gpu_monitor.git
cd gpu_monitor
pip install -r requirements-linux.txt
python main.py
```

### Launching a specific platform

`main.py` autodetects the OS and picks the right variant. To bypass detection and launch a platform directly (useful for testing or when autodetection picks the wrong one):

```bash
python -m platforms.amd_ryzen.app       # Windows / AMD Ryzen AI Max
python -m platforms.apple_silicon.app   # macOS / Apple Silicon
python -m platforms.nvidia_linux.app    # Linux / NVIDIA
```

Each variant only runs on its target OS — the AMD module needs `pywin32` + `pythonnet`, Apple Silicon needs `powermetrics`, and NVIDIA needs `nvidia-smi` in `PATH`.

## Requirements

### Common
- Python 3.11+
- `textual>=0.88.0`
- `psutil>=6.0.0`

### AMD Ryzen (Windows)
- Windows 11
- Windows Terminal (for full color and Unicode rendering)
- AMD Adrenalin drivers
- `pywin32>=307`
- `pythonnet>=3.0.3`
- `wmi>=1.5.1`
- LibreHardwareMonitor v0.9.6+ (for temps/clocks/power)

### Apple Silicon (macOS)
- macOS 12+ (Monterey or later)
- `sudo` access (optional, for GPU/power/thermal data)

### NVIDIA (Linux)
- Linux distribution with NVIDIA drivers installed
- `nvidia-smi` available in PATH

## Configuration

All paths are configurable via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `GPU_MONITOR_LHM_PATH` | `C:\Users\Office\LibreHardwareMonitor` | LHM directory (Windows) |
| `GPU_MONITOR_XRT_SMI` | `C:\Windows\System32\AMD\xrt-smi.exe` | xrt-smi path (Windows) |

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit |
| `p` | Pause / resume refresh |
| `r` | Reset sparkline history |
| `v` | Toggle process table |
| `c` | Toggle CPU panel |
| `l` | Toggle CSV logging |

## Architecture

```
gpu_monitor/
├── main.py                     # Platform detection + entry point
├── common/                     # Shared types & utilities
│   ├── types.py               # GPUStats, CPUStats, MemoryStats, etc.
│   ├── config.py              # Base configuration
│   ├── logger.py              # CSV logging
│   └── widgets/util.py        # bar(), fmt_mb(), fmt_watts()
├── platforms/
│   ├── amd_ryzen/             # AMD Ryzen (Windows)
│   │   ├── collectors/        # GPU PDH, LHM, NPU, process memory
│   │   ├── widgets/           # Platform-specific UI
│   │   ├── app.py             # Textual application
│   │   └── config.py          # AMD-specific settings
│   ├── apple_silicon/         # Apple Silicon (macOS)
│   │   ├── collectors/        # psutil, vm_stat, powermetrics
│   │   ├── widgets/
│   │   ├── app.py
│   │   └── config.py
│   └── nvidia_linux/           # NVIDIA (Linux)
│       ├── collectors/        # nvidia-smi, psutil
│       ├── widgets/
│       ├── app.py
│       └── config.py
└── requirements.txt
```

### Data Sources

#### AMD Ryzen (Windows)

| Metric | Source |
|--------|--------|
| GPU engine utilization | Windows Performance Counters (`win32pdh`) |
| GPU temps/clocks/power | LibreHardwareMonitor DLL (`pythonnet`) |
| GPU / process memory | Windows Performance Counters |
| NPU | `xrt-smi examine --report aie-partitions` |
| CPU | LibreHardwareMonitor DLL |
| System RAM | `psutil` |

#### Apple Silicon (macOS)

| Metric | Source | Sudo Required |
|--------|--------|---------------|
| CPU load | `psutil.cpu_percent()` | No |
| Memory | `psutil.virtual_memory()` + `vm_stat` | No |
| GPU active % / freq | `powermetrics --samplers gpu_power` | Yes |
| Power draw | `powermetrics --samplers cpu_power,gpu_power` | Yes |
| Thermal pressure | `powermetrics --samplers thermal` / `memory_pressure` | Yes / No |

#### NVIDIA (Linux)

| Metric | Source | Sudo Required |
|--------|--------|---------------|
| GPU utilization/mem | `nvidia-smi` | No |
| GPU power/temp | `nvidia-smi` | No |
| CPU load | `psutil.cpu_percent()` | No |
| System RAM | `psutil.virtual_memory()` | No |

## GPU Stress Test

### AMD (Windows)

```bat
pip install pygame PyOpenGL
python stress.py
```

### Apple (macOS)

Use any GPU-intensive app or:
```bash
# Install gfxCardStatus or similar to force discrete GPU
# Or run a compute benchmark
```

## Troubleshooting

### AMD Ryzen

**GPU counters show 0% / unavailable**
Run the terminal as Administrator, or verify AMD drivers:
```bat
typeperf "\GPU Engine(*)\Utilization Percentage" -sc 1
```

**Temperature / clock / power show `--`**
Check `GPU_MONITOR_LHM_PATH` environment variable points to your LHM folder.

**NPU shows "xrt-smi not found"**
Ryzen AI drivers not installed, or `xrt-smi.exe` is missing.

### Apple Silicon

**GPU shows "requires sudo powermetrics"**
Run with `sudo` once to authorize, or run `sudo powermetrics` manually first:
```bash
sudo powermetrics --samplers cpu_power,gpu_power,thermal -i 1000 -n 1
```

**CPU frequencies not showing**
Require `sudo` for powermetrics. Without sudo, only load % is available.

**Thermal shows "Unknown"**
System may not be reporting thermal pressure. Check with `memory_pressure` command.

## Known Limitations

### macOS (Apple Silicon)
- **No per-process GPU tracking** — macOS has no public API equivalent to Windows PDH GPU process counters
- **GPU requires sudo** — powermetrics is the only way to access GPU utilization/power
- **ANE (Neural Engine) not exposed** — powermetrics shows `ane_power` but it's not yet parsed
- **CPU temperature not available** — No public API on macOS

## Dependencies

```
textual>=0.88.0
psutil>=6.0.0

# Windows only:
pywin32>=307
wmi>=1.5.1
pythonnet>=3.0.3
```

## License

Apache 2.0 — Copyright 2026 dagacha
