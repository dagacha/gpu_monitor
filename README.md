# gpu_monitor

An htop-like terminal GPU/CPU/NPU monitor built for the **AMD Ryzen AI Max 395** (and similar Ryzen AI Max series APUs) on Windows 11.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%2011-blue)
![GPU](https://img.shields.io/badge/GPU-AMD%20Radeon%208060S%20%2F%20RDNA-red)

## What it shows

| Panel | Metrics |
|-------|---------|
| **GPU** | Per-engine utilization (3D / Compute / Copy / Video), 60s sparkline, temperature, core clock, memory clock, SoC clock, GPU power |
| **NPU** | XDNA partitions, HW contexts, GOPS, XRT / firmware versions (via `xrt-smi`) |
| **Memory** | GPU dedicated memory, GPU shared memory, system RAM — all from the 128 GB UMA pool |
| **Processes** | Top GPU memory consumers (local + shared), refreshed every 5s |
| **CPU** | Per-core load bars + effective clock (GHz), package temperature and power |
| **SoC Power** | Combined CPU + GPU power draw |

## Hardware

Tested on:
- **BosGame M5 AI** — AMD Ryzen AI Max+ 395 w/ Radeon 8060S, 128 GB unified RAM, Windows 11 Pro

Should work on any **Ryzen AI Max 300/395** system with Windows 11 and AMD Adrenalin drivers installed.

## Requirements

- Python 3.11+
- [Windows Terminal](https://aka.ms/terminal) (for full color and Unicode rendering)
- AMD Adrenalin drivers (for GPU performance counters)
- `xrt-smi.exe` at `C:\Windows\System32\AMD\` — ships with Ryzen AI drivers

## Setup

### 1. Clone

```bat
git clone https://github.com/dagacha/gpu_monitor.git
cd gpu_monitor
```

### 2. Install Python dependencies

```bat
pip install -r requirements.txt
```

### 3. LibreHardwareMonitor (for temperature, clocks, power)

Download [LibreHardwareMonitor v0.9.6+](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases) and extract to:

```
C:\Users\<YourName>\LibreHardwareMonitor\
```

Then update the path in `collectors/hw_monitor.py`:

```python
_LHM_PATH = r"C:\Users\<YourName>\LibreHardwareMonitor"
```

The app uses the LHM DLL directly via `pythonnet` — no need to run LHM manually or enable its WMI service.

> Without LHM, the app still runs — temperature, clock, and power fields show `--`.

### 4. Run

```bat
python app.py
```

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit |
| `p` | Pause / resume refresh |
| `r` | Reset sparkline history |
| `v` | Toggle process table |
| `c` | Toggle CPU panel |
| `l` | Toggle CSV logging (saves to `gpu_log_YYYYMMDD_HHMMSS.csv`) |

## Architecture

```
gpu_monitor/
├── app.py                      # Textual app, keybindings, layout
├── logger.py                   # CSV logging
├── collectors/
│   ├── gpu_pdh.py              # GPU utilization + memory (Windows PDH)
│   ├── hw_monitor.py           # GPU/CPU temps, clocks, power (LHM DLL)
│   ├── npu.py                  # NPU status (xrt-smi)
│   └── process_gpu.py          # Per-process GPU memory (Windows PDH)
└── widgets/
    ├── gpu_panel.py            # GPU gauges + sparkline
    ├── mem_panel.py            # UMA memory bars
    ├── npu_panel.py            # NPU partition / context display
    ├── cpu_panel.py            # Per-core CPU bars + clocks
    └── process_table.py        # GPU process list
```

### Data sources

| Metric | Source |
|--------|--------|
| GPU engine utilization | Windows Performance Counters (`win32pdh`) |
| GPU D3D load, temperature, clocks, power | LibreHardwareMonitor DLL (`pythonnet`) |
| GPU / process memory | Windows Performance Counters |
| NPU partitions, contexts, GOPS | `xrt-smi examine --report aie-partitions` |
| CPU per-core load + effective clock | LibreHardwareMonitor DLL |
| System RAM | `psutil` |

## GPU stress test

```bat
pip install pygame PyOpenGL
python stress.py
```

Opens an OpenGL window at uncapped FPS to verify the 3D engine counter responds.

## Troubleshooting

**GPU counters show 0% / unavailable**
Run the terminal as Administrator, or verify AMD drivers are installed:
```bat
typeperf "\GPU Engine(*)\Utilization Percentage" -sc 1
```

**Temperature / clock / power show `--`**
Check the `_LHM_PATH` in `collectors/hw_monitor.py` points to your LHM folder.

**NPU shows "xrt-smi not found"**
Ryzen AI drivers not installed, or `C:\Windows\System32\AMD\xrt-smi.exe` is missing.

**Blank screen / no color**
Use Windows Terminal, not the classic Command Prompt or PowerShell console.

## Dependencies

```
textual>=0.88.0
pywin32>=307
psutil>=6.0.0
wmi>=1.5.1
pythonnet>=3.0.3
```
