"""PySide6.QtWidgets shim — PySide2.QtWidgets + exec() aliases."""

from PySide2.QtWidgets import *  # noqa: F403
from PySide2 import QtWidgets as _QtWidgets
from PySide2.QtWidgets import __all__ as _qtwidgets_all

__all__ = list(_qtwidgets_all)


def _add_exec_alias(cls):
    if hasattr(cls, "exec_") and not hasattr(cls, "exec"):
        cls.exec = cls.exec_


for _cls in (
    _QtWidgets.QApplication,
    _QtWidgets.QDialog,
    _QtWidgets.QMenu,
    _QtWidgets.QMessageBox,
):
    _add_exec_alias(_cls)
