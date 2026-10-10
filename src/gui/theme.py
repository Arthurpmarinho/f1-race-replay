"""Glass look for the Qt windows: dark carbon backdrop, frosted panels, F1 red accents."""

import os

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QPointF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QRadialGradient
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

F1_RED = "#E10600"
TEXT = "#F2F3F5"
TEXT_DIM = "rgba(235, 238, 245, 0.55)"

CHEVRON = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "images", "controls", "chevron-down.svg")
).replace("\\", "/")

LOGO_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "images", "logos"))

FONT_FAMILIES = ["Segoe UI Variable Display", "Segoe UI", "SF Pro Display", "Inter", "Helvetica Neue", "Arial"]

STYLESHEET = f"""
* {{ color: {TEXT}; }}

QDialog, QMessageBox, QProgressDialog {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1A1C24, stop:1 #101217);
}}

QFrame#glass {{
    background: rgba(255, 255, 255, 0.055);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 18px;
}}

QLabel {{ background: transparent; }}
QLabel#brand {{
    color: {F1_RED};
    font-size: 26px;
    font-weight: 800;
    font-style: italic;
}}
QLabel#title {{ font-size: 26px; font-weight: 600; }}
QLabel#sectionTitle {{
    color: {TEXT_DIM};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.5px;
}}
QLabel#eventName {{ font-size: 17px; font-weight: 600; }}
QLabel#muted {{ color: {TEXT_DIM}; font-size: 12px; }}

QPushButton {{
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 12px;
    padding: 9px 16px;
    font-weight: 500;
}}
QPushButton:hover {{
    background: rgba(255, 255, 255, 0.14);
    border-color: rgba(255, 255, 255, 0.22);
}}
QPushButton:pressed {{ background: rgba(225, 6, 0, 0.35); border-color: rgba(225, 6, 0, 0.6); }}
QPushButton#session {{ text-align: left; padding: 12px 16px; font-size: 14px; }}
QPushButton#session:hover {{
    background: rgba(225, 6, 0, 0.18);
    border-color: rgba(225, 6, 0, 0.55);
}}
QPushButton#primary, QPushButton#session[primary="true"] {{
    background: {F1_RED};
    border: 1px solid rgba(255, 255, 255, 0.18);
    font-weight: 600;
}}
QPushButton#primary:hover, QPushButton#session[primary="true"]:hover {{ background: #F2200F; }}

QComboBox, QLineEdit {{
    background: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 12px;
    padding: 8px 14px;
    min-height: 18px;
    selection-background-color: rgba(225, 6, 0, 0.45);
}}
QComboBox:hover, QLineEdit:hover {{ background: rgba(255, 255, 255, 0.11); }}
QComboBox:focus, QLineEdit:focus {{ border-color: rgba(225, 6, 0, 0.7); }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: url({CHEVRON}); width: 12px; height: 8px; margin-right: 12px; }}
QComboBox QAbstractItemView {{
    background: #1B1D24;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    padding: 4px;
    outline: none;
    selection-background-color: rgba(225, 6, 0, 0.35);
}}

QTreeWidget {{
    background: transparent;
    border: none;
    outline: none;
    font-size: 13px;
}}
QTreeWidget::item {{
    padding: 9px 4px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}}
QTreeWidget::item:hover {{ background: rgba(255, 255, 255, 0.06); }}
QTreeWidget::item:selected {{ background: rgba(225, 6, 0, 0.22); color: {TEXT}; }}
QHeaderView {{ background: transparent; }}
QHeaderView::section {{
    background: transparent;
    color: {TEXT_DIM};
    border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.10);
    padding: 8px 4px;
    font-size: 11px;
    font-weight: 600;
}}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px 2px; }}
QScrollBar::handle:vertical {{ background: rgba(255, 255, 255, 0.18); border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: rgba(255, 255, 255, 0.30); }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ height: 0; background: none; }}
QScrollBar:horizontal {{ height: 0; }}

QGroupBox {{
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 14px;
    margin-top: 26px;
    padding: 16px 14px 12px 14px;
    font-weight: 600;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 6px; top: 2px; color: {TEXT_DIM}; }}

QProgressBar {{
    background: rgba(255, 255, 255, 0.08);
    border: none;
    border-radius: 3px;
    max-height: 6px;
}}
QProgressBar::chunk {{ background: {F1_RED}; border-radius: 3px; }}

QToolTip {{
    background: #1B1D24;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    padding: 6px 8px;
}}
"""


def apply_theme(app):
    font = QFont()
    font.setFamilies(FONT_FAMILIES)
    font.setPixelSize(13)
    app.setFont(font)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)


class Backdrop(QWidget):
    """Carbon gradient with soft red light, so the translucent panels read as glass."""

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        base = QLinearGradient(0, 0, w, h)
        base.setColorAt(0.0, QColor("#16181F"))
        base.setColorAt(1.0, QColor("#0B0C10"))
        p.fillRect(self.rect(), base)

        for cx, cy, radius, color in (
            (0.08, 0.0, 0.75, QColor(225, 6, 0, 70)),
            (0.95, 1.0, 0.65, QColor(255, 70, 40, 34)),
            (0.60, 0.35, 0.45, QColor(90, 110, 160, 22)),
        ):
            glow = QRadialGradient(QPointF(cx * w, cy * h), radius * max(w, h))
            glow.setColorAt(0.0, color)
            glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillRect(self.rect(), glow)
        p.end()


def fade_in(widget, duration=220):
    """Fade a widget in; the effect is removed afterwards so it costs nothing at rest."""
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    anim.finished.connect(lambda: widget.setGraphicsEffect(None))
    anim.start()
    widget._fade_anim = anim


def logo_pixmap(name, height):
    """Logo from images/logos/<name>.svg or .png, or None when the file isn't there."""
    for ext in (".svg", ".png"):
        path = os.path.join(LOGO_DIR, name + ext)
        if os.path.exists(path):
            icon = QIcon(path)
            size = icon.actualSize(QSize(height * 20, height))
            return icon.pixmap(size)
    return None
