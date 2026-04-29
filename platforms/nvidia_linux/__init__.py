"""NVIDIA Linux platform plugin for gpu_monitor.

Supports NVIDIA GPUs on Linux via nvidia-smi and psutil.
"""
from __future__ import annotations

import os
import sys

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from platforms.nvidia_linux.collectors import NvidiaLinuxCollectors
from platforms.nvidia_linux.app import NvidiaLinuxMonitorApp

__all__ = ["NvidiaLinuxCollectors", "NvidiaLinuxMonitorApp"]
