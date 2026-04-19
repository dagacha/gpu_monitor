"""Main entry point for gpu_monitor — detects platform and launches appropriate monitor."""
from __future__ import annotations

import platform
import sys

def main() -> None:
    """Detect platform and launch appropriate monitor app."""
    system = platform.system()

    if system == "Windows":
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
            print("Make sure you have psutil installed: pip install psutil")
            sys.exit(1)

    else:
        print(f"Unsupported platform: {system}")
        print("Supported platforms: Windows (AMD Ryzen), macOS (Apple Silicon)")
        sys.exit(1)


if __name__ == "__main__":
    main()
