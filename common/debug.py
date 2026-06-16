"""Lightweight debug logging for gpu_monitor collectors.

Collectors deliberately swallow exceptions so the TUI stays alive when a
data source is missing, but that makes diagnosing "shows --/unavailable"
situations hard. This logger is silent by default and only emits when
``GPU_MONITOR_DEBUG`` is set, writing to a file (never stdout/stderr, so
the live TUI is never corrupted).

Usage:
    from common.debug import get_logger
    log = get_logger(__name__)
    ...
    except Exception:
        log.debug("powermetrics sample failed", exc_info=True)

Environment variables:
    GPU_MONITOR_DEBUG       enable when set to 1/true/yes/on
    GPU_MONITOR_DEBUG_LOG   log file path (default: gpu_monitor_debug.log)
"""
from __future__ import annotations

import logging
import os

_ROOT_NAME = "gpu_monitor"
_configured = False


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


def _configure_root() -> None:
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger(_ROOT_NAME)
    root.propagate = False

    if _truthy(os.environ.get("GPU_MONITOR_DEBUG")):
        path = os.environ.get("GPU_MONITOR_DEBUG_LOG", "gpu_monitor_debug.log")
        try:
            handler: logging.Handler = logging.FileHandler(path)
        except Exception:
            handler = logging.NullHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)
    else:
        root.addHandler(logging.NullHandler())
        root.setLevel(logging.CRITICAL)


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a gpu_monitor child logger, configuring the root once."""
    _configure_root()
    if name:
        return logging.getLogger(f"{_ROOT_NAME}.{name}")
    return logging.getLogger(_ROOT_NAME)
