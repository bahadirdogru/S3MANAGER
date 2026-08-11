"""Toolbar theme toggle — ay (koyu) / güneş (açık)."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QFrame, QLabel


class ThemeSwitch(QWidget):
    """Pill-shaped dark/light mode toggle with moon and sun icons."""

    theme_changed = Signal(str)

    _WIDTH = 64
    _HEIGHT = 32
    _THUMB_W = 28
    _THUMB_H = 24
    _PAD = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ThemeSwitch")
        self.setFixedSize(self._WIDTH, self._HEIGHT)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Koyu tema")
        self._mode = "dark"
        self._block_signal = False

        self.thumb = QFrame(self)
        self.thumb.setObjectName("ThemeSwitchThumb")
        self.thumb.setFixedSize(self._THUMB_W, self._THUMB_H)

        self.lbl_moon = QLabel("🌙", self)
        self.lbl_moon.setObjectName("ThemeSwitchIcon")
        self.lbl_moon.setAlignment(Qt.AlignCenter)
        self.lbl_moon.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.lbl_sun = QLabel("☀️", self)
        self.lbl_sun.setObjectName("ThemeSwitchIcon")
        self.lbl_sun.setAlignment(Qt.AlignCenter)
        self.lbl_sun.setAttribute(Qt.WA_TransparentForMouseEvents)

        self._layout_icons()
        self._position_thumb()
        self._update_icon_state()

    def mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str, emit: bool = False):
        normalized = "light" if str(mode).strip().lower() == "light" else "dark"
        if normalized == self._mode and not emit:
            self._position_thumb()
            self._update_icon_state()
            return
        self._mode = normalized
        self.setToolTip("Açık tema" if self._mode == "light" else "Koyu tema")
        self._position_thumb()
        self._update_icon_state()
        if emit and not self._block_signal:
            self.theme_changed.emit(self._mode)

    def _layout_icons(self):
        half = self._WIDTH // 2
        icon_h = self._HEIGHT
        self.lbl_moon.setGeometry(0, 0, half, icon_h)
        self.lbl_sun.setGeometry(half, 0, half, icon_h)
        self.thumb.raise_()
        self.lbl_moon.raise_()
        self.lbl_sun.raise_()

    def _position_thumb(self):
        y = (self._HEIGHT - self._THUMB_H) // 2
        if self._mode == "dark":
            x = self._PAD
        else:
            x = self._WIDTH - self._THUMB_W - self._PAD
        self.thumb.move(x, y)

    def _update_icon_state(self):
        self.lbl_moon.setProperty("active", self._mode == "dark")
        self.lbl_sun.setProperty("active", self._mode == "light")
        self.lbl_moon.style().unpolish(self.lbl_moon)
        self.lbl_moon.style().polish(self.lbl_moon)
        self.lbl_sun.style().unpolish(self.lbl_sun)
        self.lbl_sun.style().polish(self.lbl_sun)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)
        half = self.width() // 2
        if event.position().x() < half:
            new_mode = "dark"
        else:
            new_mode = "light"
        if new_mode != self._mode:
            self.set_mode(new_mode, emit=True)
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_icons()
        self._position_thumb()
