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
    filled = int(pct / 100 * width)
    empty = width - filled
    color = "red" if pct >= 80 else "yellow" if pct >= 50 else "green"
    bar_str = f"[{'█' * filled}{'░' * empty}]"
    if show_pct:
        return f"[{color}]{bar_str}[/] {pct:5.1f}%"
    return f"[{color}]{bar_str}[/]"
