"""Shared utility functions for widgets."""
from __future__ import annotations


def bar(pct: float, width: int = 28, show_pct: bool = True) -> str:
    """Render a color-coded ASCII progress bar.

    Args:
        pct: Percentage value (0-100)
        width: Width of the bar in characters (default: 28)
        show_pct: Whether to append the percentage value (default: True)

    Returns:
        Rich-formatted string with color-coded bar
    """
    pct = max(0.0, min(pct, 100.0))
    filled = int(pct / 100 * width)
    empty = width - filled
    color = "red" if pct >= 80 else "yellow" if pct >= 50 else "green"
    bar_str = f"[{'█' * filled}{'░' * empty}]"
    if show_pct:
        return f"[{color}]{bar_str}[/] {pct:5.1f}%"
    return f"[{color}]{bar_str}[/]"


def fmt_mb(mb: float) -> str:
    """Format megabytes to human-readable string.

    Args:
        mb: Value in megabytes

    Returns:
        Formatted string (e.g., "16.0 GB" or "512 MB")
    """
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{mb:.0f} MB"


def fmt_hz(hz: float) -> str:
    """Format frequency in Hz to human-readable string.

    Args:
        hz: Frequency in Hz

    Returns:
        Formatted string (e.g., "3.2 GHz" or "1200 MHz")
    """
    if hz >= 1e9:
        return f"{hz / 1e9:.2f} GHz"
    if hz >= 1e6:
        return f"{hz / 1e6:.0f} MHz"
    if hz >= 1e3:
        return f"{hz / 1e3:.0f} KHz"
    return f"{hz:.0f} Hz"


def fmt_watts(w: float) -> str:
    """Format power in watts.

    Args:
        w: Power in watts

    Returns:
        Formatted string (e.g., "15.3 W")
    """
    return f"{w:.1f} W"
