"""Main entry point for gpu_monitor — detects platform and launches appropriate monitor."""
from __future__ import annotations

import os
import platform
import sys


def _has_nvidia(system: str) -> bool:
    """Check if nvidia-smi is available for the current OS."""
    override = os.environ.get("NVSMI_PATH")
    if override:
        return os.path.isfile(override)
    if system == "Windows":
        candidates = [
            r"C:\Windows\System32\nvidia-smi.exe",
            r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe",
        ]
    else:
        candidates = ["/usr/bin/nvidia-smi", "/usr/local/bin/nvidia-smi"]
    return any(os.path.isfile(c) for c in candidates)


def main() -> None:
    """Detect platform and launch appropriate monitor app."""
    system = platform.system()

    if system == "Windows":
        if _has_nvidia(system):
            try:
                from platforms.nvidia_windows import NvidiaWindowsMonitorApp
                print("Detected: NVIDIA GPU (Windows)")
                NvidiaWindowsMonitorApp().run()
                return
            except ImportError as e:
                print(f"Error loading NVIDIA Windows platform: {e}")
                print("Falling back to AMD Ryzen detection...")
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
        if _has_nvidia(system):
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
        print("Supported platforms: Windows (AMD Ryzen), macOS (Apple Silicon), Linux (NVIDIA)")
        sys.exit(1)


if __name__ == "__main__":
    main()
