"""Main entry point for gpu_monitor — detects platform and launches appropriate monitor."""
from __future__ import annotations

import os
import platform
import shutil
import sys


def _check_python_version() -> None:
    if sys.version_info < (3, 10) or sys.version_info >= (3, 16):
        print(f"Python 3.10–3.15 required (got {sys.version.split()[0]})")
        sys.exit(1)


def _has_nvidia_linux() -> bool:
    """Check if nvidia-smi is available on Linux."""
    path = os.environ.get("NVSMI_PATH", "/usr/bin/nvidia-smi")
    return os.path.isfile(path)


def _has_nvidia_windows() -> bool:
    """Check if nvidia-smi is available on Windows."""
    # Check common locations
    nvidia_smi_paths = [
        r"C:\Windows\System32\nvidia-smi.exe",
        r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe",
    ]
    for path in nvidia_smi_paths:
        if os.path.isfile(path):
            return True
    # Also check PATH
    return shutil.which("nvidia-smi") is not None


def main() -> None:
    """Detect platform and launch appropriate monitor app."""
    _check_python_version()
    system = platform.system()

    if system == "Windows":
        # Check for NVIDIA GPU first
        if _has_nvidia_windows():
            try:
                from platforms.nvidia_windows import NvidiaWindowsMonitorApp
                print("Detected: NVIDIA GPU (Windows)")
                NvidiaWindowsMonitorApp().run()
            except ImportError as e:
                print(f"Error loading NVIDIA Windows platform: {e}")
                sys.exit(1)
        else:
            # Fall back to AMD Ryzen
            try:
                from platforms.amd_ryzen import AMDRyzenMonitorApp
                print("Detected: AMD Ryzen (Windows)")
                AMDRyzenMonitorApp().run()
            except ImportError as e:
                print(f"Error loading AMD Ryzen platform: {e}")
                print("Make sure you're on Windows with pywin32 and pythonnet installed.")
                sys.exit(1)

    elif system == "Darwin":
        try:
            from platforms.apple_silicon import AppleSiliconMonitorApp
            print("Detected: Apple Silicon (macOS)")
            AppleSiliconMonitorApp().run()
        except ImportError as e:
            print(f"Error loading Apple Silicon platform: {e}")
            print("\nTroubleshooting:")
            print("1. Without sudo: pip install textual psutil")
            print("2. With sudo, use the full Python path:")
            print(f"   sudo $(which python3) main.py")
            print("\nOr install dependencies for system Python:")
            print("   sudo pip install textual psutil")
            sys.exit(1)

    elif system == "Linux":
        if _has_nvidia_linux():
            try:
                from platforms.nvidia_linux import NvidiaLinuxMonitorApp
                print("Detected: NVIDIA GPU (Linux)")
                NvidiaLinuxMonitorApp().run()
            except ImportError as e:
                print(f"Error loading NVIDIA Linux platform: {e}")
                sys.exit(1)
        else:
            print(f"No NVIDIA GPU detected (nvidia-smi not found).")
            print("Supported on Linux: NVIDIA GPUs via nvidia-smi.")
            sys.exit(1)

    else:
        print(f"Unsupported platform: {system}")
        print("Supported platforms: Windows (NVIDIA/AMD), macOS (Apple Silicon), Linux (NVIDIA)")
        sys.exit(1)


if __name__ == "__main__":
    main()
