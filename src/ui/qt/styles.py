"""WhatsApp-inspired dark theme (siyah + yeşil) — katmanlı derinlik."""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect

# Renk sabitleri — inline stiller için
WA_BG = "#0B141A"
WA_BG_PANEL = "#151F26"
WA_BG_DIALOG = "#1A252D"
WA_BG_ELEVATED = "#243038"
WA_BG_HOVER = "#2A3942"
WA_GREEN = "#00A884"
WA_GREEN_BRIGHT = "#25D366"
WA_GREEN_DARK = "#075E54"
WA_GREEN_HOVER = "#06CF9C"
WA_TEXT = "#E9EDEF"
WA_TEXT_SECONDARY = "#AEBAC1"
WA_TEXT_MUTED = "#A0ADB4"
WA_BORDER = "#3A4A54"
WA_BORDER_SUBTLE = "#2A3942"
WA_ERROR = "#EA0038"
WA_SUCCESS = "#25D366"
WA_WARNING = "#FFB800"


def apply_dialog_elevation(widget):
    """Dialog'a gölge efekti ekler (QSS gölge desteklemez)."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(28)
    effect.setOffset(0, 6)
    effect.setColor(QColor(0, 0, 0, 120))
    widget.setGraphicsEffect(effect)


def get_dark_theme():
    return f"""
    QMainWindow {{
        background-color: {WA_BG};
        color: {WA_TEXT};
    }}

    QDialog {{
        background-color: {WA_BG_DIALOG};
        color: {WA_TEXT};
        border: 1px solid {WA_BORDER};
        border-radius: 12px;
    }}

    QDialog#ElevatedDialog {{
        background-color: {WA_BG_DIALOG};
        border: 1px solid {WA_BORDER};
    }}

    QFrame#ToolbarFrame {{
        background-color: {WA_BG_PANEL};
        border-bottom: 1px solid {WA_BORDER};
    }}

    QFrame#BreadcrumbFrame {{
        background-color: {WA_BG_PANEL};
        border-bottom: 1px solid {WA_BORDER};
    }}

    QFrame#FormFrame {{
        background-color: {WA_BG_ELEVATED};
        border: 1px solid {WA_BORDER_SUBTLE};
        border-radius: 12px;
    }}

    QFrame#UploadHeader {{
        background-color: transparent;
        border-bottom: 1px solid {WA_BORDER_SUBTLE};
        padding-bottom: 4px;
    }}

    QPushButton {{
        background-color: {WA_GREEN};
        color: #FFFFFF;
        border-radius: 6px;
        padding: 6px 15px;
        font-size: 13px;
        font-weight: bold;
        border: none;
    }}

    QPushButton:hover {{
        background-color: {WA_GREEN_HOVER};
    }}

    QPushButton:disabled {{
        background-color: {WA_BG_HOVER};
        color: {WA_TEXT_MUTED};
    }}

    QPushButton#SecondaryButton {{
        background-color: {WA_BG_HOVER};
        color: {WA_TEXT};
    }}

    QPushButton#SecondaryButton:hover {{
        background-color: {WA_BORDER};
    }}

    QPushButton#BreadcrumbButton {{
        background-color: transparent;
        color: {WA_GREEN_BRIGHT};
        border: none;
        padding: 2px 6px;
        font-size: 13px;
        font-weight: normal;
        text-align: left;
    }}

    QPushButton#BreadcrumbButton:hover {{
        background-color: {WA_BG_HOVER};
        color: {WA_GREEN_HOVER};
    }}

    QLabel#BreadcrumbSep {{
        color: {WA_TEXT_MUTED};
        font-size: 13px;
    }}

    QLineEdit {{
        background-color: {WA_BG_ELEVATED};
        color: {WA_TEXT};
        border: 1px solid {WA_BORDER};
        border-radius: 6px;
        padding: 8px;
        font-size: 14px;
    }}

    QLineEdit:focus {{
        border: 1px solid {WA_GREEN};
    }}

    QComboBox {{
        background-color: {WA_BG_ELEVATED};
        color: {WA_TEXT};
        border: 1px solid {WA_BORDER};
        border-radius: 6px;
        padding: 8px;
        font-size: 14px;
    }}

    QComboBox:hover {{
        border: 1px solid {WA_GREEN_DARK};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}

    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid {WA_TEXT};
        margin-right: 8px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {WA_BG_ELEVATED};
        color: {WA_TEXT};
        selection-background-color: {WA_GREEN_DARK};
        border: 1px solid {WA_BORDER};
    }}

    QRadioButton {{
        color: {WA_TEXT};
        font-size: 14px;
        spacing: 8px;
    }}

    QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 9px;
        border: 2px solid {WA_BORDER};
        background-color: {WA_BG_ELEVATED};
    }}

    QRadioButton::indicator:checked {{
        background-color: {WA_GREEN};
        border: 2px solid {WA_GREEN};
    }}

    QTreeView {{
        background-color: {WA_BG};
        color: {WA_TEXT};
        border: none;
        outline: none;
        alternate-background-color: {WA_BG_PANEL};
    }}

    QTreeView::item {{
        height: 38px;
        border-bottom: 1px solid {WA_BG_PANEL};
        color: {WA_TEXT};
    }}

    QTreeView::item:selected {{
        background-color: {WA_GREEN_DARK};
        color: #FFFFFF;
    }}

    QTreeView::item:hover {{
        background-color: {WA_BG_HOVER};
    }}

    QHeaderView::section {{
        background-color: {WA_BG_ELEVATED};
        color: {WA_TEXT};
        padding: 8px 5px;
        border: none;
        border-bottom: 2px solid {WA_GREEN_DARK};
        font-weight: bold;
        font-size: 13px;
    }}

    QLabel {{
        color: {WA_TEXT};
    }}

    QLabel#StatusLabel {{
        color: {WA_TEXT_SECONDARY};
        font-size: 13px;
    }}

    QLabel#UploadSummaryLabel {{
        color: {WA_TEXT_SECONDARY};
        font-size: 13px;
    }}

    QLabel#ProgressMeta {{
        color: {WA_TEXT_SECONDARY};
        font-size: 11px;
    }}

    QLabel#DropZoneHint {{
        color: {WA_TEXT_MUTED};
        font-size: 13px;
    }}

    QFrame#DropZoneFrame {{
        background-color: {WA_BG_ELEVATED};
        border: 2px dashed {WA_BORDER};
        border-radius: 8px;
    }}

    QFrame#DropZoneFrame:hover {{
        border-color: {WA_GREEN_DARK};
    }}

    QWidget#UploadProgressCard {{
        background-color: {WA_BG_ELEVATED};
        border: 1px solid {WA_BORDER_SUBTLE};
        border-radius: 8px;
    }}

    QLabel#UploadFileName {{
        color: {WA_TEXT};
        font-size: 13px;
        font-weight: bold;
    }}

    QLabel#UploadFilePct {{
        color: {WA_GREEN_BRIGHT};
        font-size: 13px;
        font-weight: bold;
        min-width: 44px;
    }}

    QLabel#UploadFileSpeed {{
        color: {WA_GREEN_BRIGHT};
        font-size: 15px;
        font-weight: bold;
        min-width: 88px;
        padding-right: 8px;
    }}

    QLabel#UploadOverallPct {{
        color: {WA_TEXT_SECONDARY};
        font-size: 13px;
        font-weight: bold;
        min-width: 110px;
    }}

    QLabel#UploadOverallSpeed {{
        color: {WA_GREEN_BRIGHT};
        font-size: 28px;
        font-weight: bold;
        min-width: 130px;
        letter-spacing: 0.5px;
        padding-left: 12px;
    }}

    QWidget#UploadProgressCard QLabel#ProgressMeta {{
        color: {WA_TEXT_SECONDARY};
        font-size: 11px;
    }}

    QWidget#UploadProgressCard QProgressBar {{
        background-color: {WA_BG_PANEL};
        border: none;
        border-radius: 5px;
    }}

    QWidget#UploadProgressCard QProgressBar::chunk {{
        background-color: {WA_GREEN_BRIGHT};
        border-radius: 5px;
    }}

    QLabel#UploadMultipartInfo {{
        color: {WA_WARNING};
        font-size: 10px;
    }}

    QListWidget {{
        background-color: {WA_BG_PANEL};
        color: {WA_TEXT};
        border: 1px solid {WA_BORDER};
        border-radius: 6px;
        outline: none;
    }}

    QListWidget#UploadFileList {{
        background-color: {WA_BG_PANEL};
        alternate-background-color: {WA_BG_ELEVATED};
    }}

    QListWidget#UploadFileList::item {{
        background-color: transparent;
        color: {WA_TEXT};
        padding: 0;
        border-bottom: 1px solid {WA_BORDER_SUBTLE};
    }}

    QListWidget#UploadFileList::item:selected {{
        background-color: {WA_GREEN_DARK};
    }}

    QListWidget#UploadFileList::item:hover {{
        background-color: {WA_BG_HOVER};
    }}

    QWidget#UploadFileRow {{
        background-color: transparent;
    }}

    QLabel#UploadFileRowLabel {{
        color: {WA_TEXT};
        font-size: 13px;
        background-color: transparent;
    }}

    QListWidget::item {{
        padding: 4px;
        border-bottom: 1px solid {WA_BORDER_SUBTLE};
    }}

    QListWidget::item:selected {{
        background-color: {WA_GREEN_DARK};
    }}

    QListWidget::item:hover {{
        background-color: {WA_BG_HOVER};
    }}

    QTreeWidget {{
        background-color: {WA_BG_PANEL};
        color: {WA_TEXT};
        border: 1px solid {WA_BORDER};
        border-radius: 6px;
        outline: none;
    }}

    QTreeWidget#UploadFileTree {{
        alternate-background-color: {WA_BG_ELEVATED};
    }}

    QTreeWidget#UploadFileTree::item {{
        color: {WA_TEXT};
        padding: 4px 2px;
    }}

    QTreeWidget#UploadFileTree::item:selected {{
        background-color: {WA_GREEN_DARK};
        color: #FFFFFF;
    }}

    QTreeWidget#UploadFileTree::item:hover {{
        background-color: {WA_BG_HOVER};
    }}

    QTreeWidget::item {{
        padding: 2px 0;
    }}

    QTreeWidget::item:selected {{
        background-color: {WA_GREEN_DARK};
    }}

    QTreeWidget::item:hover {{
        background-color: {WA_BG_HOVER};
    }}

    QProgressBar#UploadOverallProgress {{
        background-color: {WA_BG_ELEVATED};
        border: none;
        border-radius: 6px;
    }}

    QProgressBar#UploadOverallProgress::chunk {{
        background-color: {WA_GREEN_BRIGHT};
        border-radius: 6px;
    }}

    QScrollBar:vertical {{
        border: none;
        background: {WA_BG_PANEL};
        width: 10px;
        margin: 0px;
    }}

    QScrollBar::handle:vertical {{
        background: {WA_BORDER};
        min-height: 20px;
        border-radius: 5px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {WA_GREEN_DARK};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        border: none;
        background: none;
    }}

    QScrollBar:horizontal {{
        border: none;
        background: {WA_BG_PANEL};
        height: 10px;
        margin: 0px;
    }}

    QScrollBar::handle:horizontal {{
        background: {WA_BORDER};
        min-width: 20px;
        border-radius: 5px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background: {WA_GREEN_DARK};
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        border: none;
        background: none;
    }}

    QScrollArea {{
        border: none;
        background-color: {WA_BG_PANEL};
    }}

    QScrollArea#UploadScroll {{
        background-color: {WA_BG_PANEL};
        border: 1px solid {WA_BORDER_SUBTLE};
        border-radius: 8px;
    }}

    QScrollArea#UploadScroll::viewport {{
        background-color: {WA_BG_PANEL};
        border: none;
    }}

    QWidget#UploadScrollContent {{
        background-color: {WA_BG_PANEL};
        color: {WA_TEXT};
    }}

    QProgressBar {{
        background-color: {WA_BG_ELEVATED};
        border: none;
        border-radius: 5px;
    }}

    QProgressBar::chunk {{
        background-color: {WA_GREEN};
        border-radius: 5px;
    }}
    """
