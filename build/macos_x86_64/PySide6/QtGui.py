"""PySide6.QtGui shim — PySide2.QtGui + PySide6-compatible extras."""

from PySide2.QtGui import *  # noqa: F403
from PySide2.QtGui import QKeySequence
from PySide2.QtWidgets import QShortcut
from PySide2.QtGui import __all__ as _qtgui_all

__all__ = list(_qtgui_all) + ["QShortcut"]


class _StandardKey:
    """PySide6 QKeySequence.StandardKey compatibility."""

    SelectAll = QKeySequence.SelectAll
    Copy = QKeySequence.Copy
    Cut = QKeySequence.Cut
    Paste = QKeySequence.Paste
    Undo = QKeySequence.Undo
    Redo = QKeySequence.Redo
    Delete = QKeySequence.Delete
    Find = QKeySequence.Find
    HelpContents = QKeySequence.HelpContents


QKeySequence.StandardKey = _StandardKey
