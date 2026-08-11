"""WhatsApp-inspired themes (dark + light) — palette tabanlı QSS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect

if TYPE_CHECKING:
    from src.config.settings import Settings

# Semantik renkler — tema bağımsız (inline stiller için)
WA_GREEN = "#00A884"
WA_GREEN_BRIGHT = "#25D366"
WA_GREEN_DARK = "#075E54"
WA_GREEN_HOVER = "#06CF9C"
WA_ERROR = "#EA0038"
WA_SUCCESS = "#25D366"
WA_WARNING = "#FFB800"

# Geriye uyumluluk — koyu palet alias'ları
WA_BG = "#0B141A"
WA_BG_PANEL = "#151F26"
WA_BG_DIALOG = "#1A252D"
WA_BG_ELEVATED = "#243038"
WA_BG_HOVER = "#2A3942"
WA_TEXT = "#E9EDEF"
WA_TEXT_SECONDARY = "#AEBAC1"
WA_TEXT_MUTED = "#A0ADB4"
WA_BORDER = "#3A4A54"
WA_BORDER_SUBTLE = "#2A3942"


@dataclass(frozen=True)
class ThemePalette:
    bg: str
    bg_panel: str
    bg_dialog: str
    bg_elevated: str
    bg_hover: str
    text: str
    text_secondary: str
    text_muted: str
    border: str
    border_subtle: str
    green: str = WA_GREEN
    green_bright: str = WA_GREEN_BRIGHT
    green_dark: str = WA_GREEN_DARK
    green_hover: str = WA_GREEN_HOVER


DARK_PALETTE = ThemePalette(
    bg="#0B141A",
    bg_panel="#151F26",
    bg_dialog="#1A252D",
    bg_elevated="#243038",
    bg_hover="#2A3942",
    text="#E9EDEF",
    text_secondary="#AEBAC1",
    text_muted="#A0ADB4",
    border="#3A4A54",
    border_subtle="#2A3942",
)

LIGHT_PALETTE = ThemePalette(
    bg="#F0F2F5",
    bg_panel="#FFFFFF",
    bg_dialog="#FFFFFF",
    bg_elevated="#F5F6F6",
    bg_hover="#E9EDEF",
    text="#111B21",
    text_secondary="#667781",
    text_muted="#8696A0",
    border="#D1D7DB",
    border_subtle="#E9EDEF",
)

_current_mode = "dark"
_active_palette: ThemePalette = DARK_PALETTE


def _normalize_mode(mode: str) -> str:
    return "light" if mode.strip().lower() == "light" else "dark"


def get_palette(mode: str) -> ThemePalette:
    return LIGHT_PALETTE if _normalize_mode(mode) == "light" else DARK_PALETTE


def current_theme_mode() -> str:
    return _current_mode


def current_palette() -> ThemePalette:
    return _active_palette


def set_theme(mode: str) -> ThemePalette:
    global _current_mode, _active_palette
    _current_mode = _normalize_mode(mode)
    _active_palette = get_palette(_current_mode)
    return _active_palette


def apply_dialog_elevation(widget, dark: Optional[bool] = None):
    """Dialog'a gölge efekti ekler (QSS gölge desteklemez)."""
    if dark is None:
        dark = current_theme_mode() == "dark"
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(28)
    effect.setOffset(0, 6)
    if dark:
        effect.setColor(QColor(0, 0, 0, 120))
    else:
        effect.setColor(QColor(0, 0, 0, 45))
    widget.setGraphicsEffect(effect)


def build_stylesheet(palette: ThemePalette) -> str:
    p = palette
    return f"""
    QMainWindow {{
        background-color: {p.bg};
        color: {p.text};
    }}

    QWidget {{
        color: {p.text};
    }}

    QMenuBar {{
        background-color: {p.bg_panel};
        color: {p.text};
        border-bottom: 1px solid {p.border};
        padding: 2px 4px;
    }}

    QMenuBar::item {{
        background: transparent;
        padding: 4px 10px;
        border-radius: 4px;
    }}

    QMenuBar::item:selected {{
        background-color: {p.bg_hover};
    }}

    QMenu {{
        background-color: {p.bg_dialog};
        color: {p.text};
        border: 1px solid {p.border};
        padding: 4px 0;
    }}

    QMenu::item {{
        padding: 6px 24px 6px 16px;
    }}

    QMenu::item:selected {{
        background-color: {p.green_dark};
        color: #FFFFFF;
    }}

    QDialog {{
        background-color: {p.bg_dialog};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 12px;
    }}

    QDialog#ElevatedDialog {{
        background-color: {p.bg_dialog};
        border: 1px solid {p.border};
    }}

    QFrame#ToolbarFrame {{
        background-color: {p.bg_panel};
        border-bottom: 1px solid {p.border};
    }}

    QFrame#BreadcrumbFrame {{
        background-color: {p.bg_panel};
        border-bottom: 1px solid {p.border};
    }}

    QFrame#FormFrame {{
        background-color: {p.bg_elevated};
        border: 1px solid {p.border_subtle};
        border-radius: 12px;
    }}

    QFrame#UploadHeader {{
        background-color: transparent;
        border-bottom: 1px solid {p.border_subtle};
        padding-bottom: 4px;
    }}

    QWidget#ThemeSwitch {{
        background-color: {p.bg_elevated};
        border: 1px solid {p.border_subtle};
        border-radius: 16px;
    }}

    QFrame#ThemeSwitchThumb {{
        background-color: {p.green};
        border-radius: 12px;
        border: none;
    }}

    QLabel#ThemeSwitchIcon {{
        background: transparent;
        font-size: 14px;
        color: {p.text_muted};
    }}

    QLabel#ThemeSwitchIcon[active="true"] {{
        color: {p.text};
    }}

    QPushButton {{
        background-color: {p.green};
        color: #FFFFFF;
        border-radius: 6px;
        padding: 6px 15px;
        font-size: 13px;
        font-weight: bold;
        border: none;
    }}

    QPushButton:hover {{
        background-color: {p.green_hover};
    }}

    QPushButton:disabled {{
        background-color: {p.bg_hover};
        color: {p.text_muted};
    }}

    QPushButton#SecondaryButton {{
        background-color: {p.bg_hover};
        color: {p.text};
    }}

    QPushButton#SecondaryButton:hover {{
        background-color: {p.border};
    }}

    QPushButton#BreadcrumbButton {{
        background-color: transparent;
        color: {p.green_bright};
        border: none;
        padding: 2px 6px;
        font-size: 13px;
        font-weight: normal;
        text-align: left;
    }}

    QPushButton#BreadcrumbButton:hover {{
        background-color: {p.bg_hover};
        color: {p.green_hover};
    }}

    QLabel#BreadcrumbSep {{
        color: {p.text_muted};
        font-size: 13px;
    }}

    QLineEdit {{
        background-color: {p.bg_elevated};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 6px;
        padding: 8px;
        font-size: 14px;
    }}

    QLineEdit:focus {{
        border: 1px solid {p.green};
    }}

    QComboBox {{
        background-color: {p.bg_elevated};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 6px;
        padding: 8px;
        font-size: 14px;
    }}

    QComboBox:hover {{
        border: 1px solid {p.green_dark};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}

    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid {p.text};
        margin-right: 8px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {p.bg_elevated};
        color: {p.text};
        selection-background-color: {p.green_dark};
        border: 1px solid {p.border};
    }}

    QCheckBox {{
        color: {p.text};
        font-size: 14px;
        spacing: 8px;
    }}

    QRadioButton {{
        color: {p.text};
        font-size: 14px;
        spacing: 8px;
    }}

    QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 9px;
        border: 2px solid {p.border};
        background-color: {p.bg_elevated};
    }}

    QRadioButton::indicator:checked {{
        background-color: {p.green};
        border: 2px solid {p.green};
    }}

    QTreeView {{
        background-color: {p.bg};
        color: {p.text};
        border: none;
        outline: none;
        alternate-background-color: {p.bg_panel};
    }}

    QTreeView::item {{
        height: 38px;
        border-bottom: 1px solid {p.bg_panel};
        color: {p.text};
    }}

    QTreeView::item:selected {{
        background-color: {p.green_dark};
        color: #FFFFFF;
    }}

    QTreeView::item:hover {{
        background-color: {p.bg_hover};
    }}

    QHeaderView::section {{
        background-color: {p.bg_elevated};
        color: {p.text};
        padding: 8px 5px;
        border: none;
        border-bottom: 2px solid {p.green_dark};
        font-weight: bold;
        font-size: 13px;
    }}

    QLabel {{
        color: {p.text};
    }}

    QLabel#StatusLabel {{
        color: {p.text_secondary};
        font-size: 13px;
    }}

    QLabel#UploadSummaryLabel {{
        color: {p.text_secondary};
        font-size: 13px;
    }}

    QLabel#ProgressMeta {{
        color: {p.text_secondary};
        font-size: 11px;
    }}

    QLabel#DropZoneHint {{
        color: {p.text_muted};
        font-size: 13px;
    }}

    QFrame#DropZoneFrame {{
        background-color: {p.bg_elevated};
        border: 2px dashed {p.border};
        border-radius: 8px;
    }}

    QFrame#DropZoneFrame:hover {{
        border-color: {p.green_dark};
    }}

    QWidget#UploadProgressCard {{
        background-color: {p.bg_elevated};
        border: 1px solid {p.border_subtle};
        border-radius: 8px;
    }}

    QLabel#UploadFileName {{
        color: {p.text};
        font-size: 13px;
        font-weight: bold;
    }}

    QLabel#UploadFilePct {{
        color: {p.green_bright};
        font-size: 13px;
        font-weight: bold;
        min-width: 44px;
    }}

    QLabel#UploadFileSpeed {{
        color: {p.green_bright};
        font-size: 15px;
        font-weight: bold;
        min-width: 88px;
        padding-right: 8px;
    }}

    QLabel#UploadOverallPct {{
        color: {p.text_secondary};
        font-size: 13px;
        font-weight: bold;
        min-width: 110px;
    }}

    QLabel#UploadOverallSpeed {{
        color: {p.green_bright};
        font-size: 28px;
        font-weight: bold;
        min-width: 130px;
        letter-spacing: 0.5px;
        padding-left: 12px;
    }}

    QWidget#UploadProgressCard QLabel#ProgressMeta {{
        color: {p.text_secondary};
        font-size: 11px;
    }}

    QWidget#UploadProgressCard QProgressBar {{
        background-color: {p.bg_panel};
        border: none;
        border-radius: 5px;
    }}

    QWidget#UploadProgressCard QProgressBar::chunk {{
        background-color: {p.green_bright};
        border-radius: 5px;
    }}

    QLabel#UploadMultipartInfo {{
        color: {WA_WARNING};
        font-size: 10px;
    }}

    QListWidget {{
        background-color: {p.bg_panel};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 6px;
        outline: none;
    }}

    QListWidget#UploadFileList {{
        background-color: {p.bg_panel};
        alternate-background-color: {p.bg_elevated};
    }}

    QListWidget#UploadFileList::item {{
        background-color: transparent;
        color: {p.text};
        padding: 0;
        border-bottom: 1px solid {p.border_subtle};
    }}

    QListWidget#UploadFileList::item:selected {{
        background-color: {p.green_dark};
    }}

    QListWidget#UploadFileList::item:hover {{
        background-color: {p.bg_hover};
    }}

    QWidget#UploadFileRow {{
        background-color: transparent;
    }}

    QLabel#UploadFileRowLabel {{
        color: {p.text};
        font-size: 13px;
        background-color: transparent;
    }}

    QListWidget::item {{
        padding: 4px;
        border-bottom: 1px solid {p.border_subtle};
    }}

    QListWidget::item:selected {{
        background-color: {p.green_dark};
    }}

    QListWidget::item:hover {{
        background-color: {p.bg_hover};
    }}

    QTreeWidget {{
        background-color: {p.bg_panel};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 6px;
        outline: none;
    }}

    QTreeWidget#UploadFileTree {{
        alternate-background-color: {p.bg_elevated};
    }}

    QTreeWidget#UploadFileTree::item {{
        color: {p.text};
        padding: 4px 2px;
    }}

    QTreeWidget#UploadFileTree::item:selected {{
        background-color: {p.green_dark};
        color: #FFFFFF;
    }}

    QTreeWidget#UploadFileTree::item:hover {{
        background-color: {p.bg_hover};
    }}

    QTreeWidget::item {{
        padding: 2px 0;
    }}

    QTreeWidget::item:selected {{
        background-color: {p.green_dark};
    }}

    QTreeWidget::item:hover {{
        background-color: {p.bg_hover};
    }}

    QProgressBar#UploadOverallProgress {{
        background-color: {p.bg_elevated};
        border: none;
        border-radius: 6px;
    }}

    QProgressBar#UploadOverallProgress::chunk {{
        background-color: {p.green_bright};
        border-radius: 6px;
    }}

    QScrollBar:vertical {{
        border: none;
        background: {p.bg_panel};
        width: 10px;
        margin: 0px;
    }}

    QScrollBar::handle:vertical {{
        background: {p.border};
        min-height: 20px;
        border-radius: 5px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {p.green_dark};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        border: none;
        background: none;
    }}

    QScrollBar:horizontal {{
        border: none;
        background: {p.bg_panel};
        height: 10px;
        margin: 0px;
    }}

    QScrollBar::handle:horizontal {{
        background: {p.border};
        min-width: 20px;
        border-radius: 5px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background: {p.green_dark};
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        border: none;
        background: none;
    }}

    QScrollArea {{
        border: none;
        background-color: {p.bg_panel};
    }}

    QScrollArea#UploadScroll {{
        background-color: {p.bg_panel};
        border: 1px solid {p.border_subtle};
        border-radius: 8px;
    }}

    QScrollArea#UploadScroll::viewport {{
        background-color: {p.bg_panel};
        border: none;
    }}

    QWidget#UploadScrollContent {{
        background-color: {p.bg_panel};
        color: {p.text};
    }}

    QProgressBar {{
        background-color: {p.bg_elevated};
        border: none;
        border-radius: 5px;
    }}

    QProgressBar::chunk {{
        background-color: {p.green};
        border-radius: 5px;
    }}

    QFrame#PreviewPanel {{
        background-color: {p.bg_panel};
        border-left: 1px solid {p.border_subtle};
    }}

    QLabel#PreviewTitle {{
        font-size: 14px;
        font-weight: bold;
        color: {p.text};
    }}

    QLabel#PreviewMeta {{
        font-size: 12px;
        color: {p.text_muted};
    }}

    QLabel#PreviewPlaceholder {{
        color: {p.text_muted};
        padding: 16px;
    }}

    QScrollArea#PreviewScroll {{
        border: 1px solid {p.border_subtle};
        border-radius: 8px;
        background-color: {p.bg_elevated};
    }}

    QFrame#TransferPanel {{
        background-color: {p.bg_panel};
        border-top: 1px solid {p.border_subtle};
    }}

    QLabel#TransferPanelTitle {{
        font-size: 12px;
        font-weight: bold;
        color: {p.text_muted};
    }}

    QListWidget#TransferList {{
        border: 1px solid {p.border_subtle};
        border-radius: 6px;
        background-color: {p.bg_elevated};
        font-size: 11px;
    }}
    """


def get_theme(mode: Optional[str] = None) -> str:
    if mode is None:
        palette = current_palette()
    else:
        palette = get_palette(mode)
    return build_stylesheet(palette)


def get_dark_theme() -> str:
    return get_theme("dark")


def apply_app_theme(mode: str, settings: Optional["Settings"] = None, persist: bool = True) -> str:
    """Aktif paleti günceller ve QApplication stylesheet uygular."""
    normalized = _normalize_mode(mode)
    set_theme(normalized)
    qss = get_theme(normalized)
    app = QApplication.instance()
    if app is not None:
        app.setStyleSheet(qss)
    if persist and settings is not None:
        settings.save_theme_mode(normalized)
    return qss
