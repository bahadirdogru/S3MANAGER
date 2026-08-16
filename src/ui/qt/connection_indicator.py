"""Toolbar bağlantı durumu göstergesi — yeşil/kırmızı nokta + tooltip."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel


class ConnectionIndicator(QFrame):
    """Bağlantı durumunu renkli nokta ile gösterir; tıklanınca Bağlan dialogu."""

    clicked = Signal()

    _SIZE = 24
    _DOT = 12

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ConnectionIndicator")
        self.setFixedSize(self._SIZE, self._SIZE)
        self.setCursor(Qt.PointingHandCursor)
        self._connected = False
        self._connecting = False
        self._connection_tooltip = "Bağlantı bekleniyor…\nTıklayın: Bağlan"

        self.dot = QLabel(self)
        self.dot.setObjectName("ConnectionIndicatorDot")
        self.dot.setFixedSize(self._DOT, self._DOT)
        self.dot.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._center_dot()
        self._apply_state()
        self.setToolTip(self._connection_tooltip)

    def _center_dot(self):
        x = (self._SIZE - self._DOT) // 2
        y = (self._SIZE - self._DOT) // 2
        self.dot.move(x, y)

    def _apply_state(self):
        if self._connecting:
            state = "connecting"
        elif self._connected:
            state = "connected"
        else:
            state = "disconnected"
        self.setProperty("connectionState", state)
        self.dot.setProperty("connectionState", state)
        self.style().unpolish(self)
        self.style().polish(self)
        self.dot.style().unpolish(self.dot)
        self.dot.style().polish(self.dot)

    def set_status(self, connected: bool, tooltip_text: str = "", connecting: bool = False):
        """Kalıcı bağlantı durumu ve varsayılan tooltip."""
        self._connected = connected
        self._connecting = connecting
        if tooltip_text:
            self._connection_tooltip = tooltip_text
        self.setToolTip(self._connection_tooltip)
        self._apply_state()

    def set_activity(self, message: str):
        """Geçici işlem mesajı (tooltip); nokta rengi bağlantı durumunu korur."""
        if message:
            self.setToolTip(message)
        else:
            self.setToolTip(self._connection_tooltip)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)
