"""
helm/learning — AI self-improvement subsystem.

Creates the ENABLED sentinel file on first import so learning is active
by default. Delete helm/learning/ENABLED to pause all learning (kill switch).
"""

from pathlib import Path

_LEARNING_DIR = Path(__file__).parent
_ENABLED_PATH = _LEARNING_DIR / "ENABLED"


def is_learning_enabled() -> bool:
    """Return True when the ENABLED sentinel file exists."""
    return _ENABLED_PATH.exists()


def enable_learning() -> None:
    """Create the sentinel file, enabling the learning system."""
    try:
        _ENABLED_PATH.touch(exist_ok=True)
    except Exception:
        pass


def disable_learning() -> None:
    """Remove the sentinel file, pausing the learning system."""
    try:
        if _ENABLED_PATH.exists():
            _ENABLED_PATH.unlink()
    except Exception:
        pass


# Create on first import (first run bootstrap).
if not _ENABLED_PATH.exists():
    enable_learning()
