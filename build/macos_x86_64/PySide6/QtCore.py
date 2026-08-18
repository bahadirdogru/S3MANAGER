"""PySide6.QtCore shim — re-exports PySide2.QtCore."""

from PySide2.QtCore import *  # noqa: F403
from PySide2.QtCore import __all__ as _qtcore_all

__all__ = list(_qtcore_all)
