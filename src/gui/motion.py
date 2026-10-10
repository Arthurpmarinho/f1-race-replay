"""Motion for the Qt windows: short, eased transitions so the app never looks frozen.

Everything here animates window opacity, a widget's position, or a temporary opacity
effect that is removed when the animation ends, so nothing costs anything at rest.
Set "animations": false in settings.json (or F1_REPLAY_NO_ANIMATIONS=1) to turn it off.
"""

from PySide6.QtCore import (
    QEasingCurve, QParallelAnimationGroup, QPoint, QPropertyAnimation, QRectF,
    QSequentialAnimationGroup, Qt, QTimer, QVariantAnimation,
)
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath
from PySide6.QtWidgets import QDialog, QGraphicsOpacityEffect, QLabel, QVBoxLayout, QWidget

from src.lib.settings import animations_enabled

ENTER_MS = 260
EXIT_MS = 150
STAGGER_MS = 45


def _keep(owner, anim):
    """Hold a reference until the animation ends, so Python doesn't collect it mid-flight."""
    running = owner.__dict__.setdefault("_motion_anims", set())
    running.add(anim)
    anim.finished.connect(lambda: running.discard(anim))
    anim.start()


def slide_in(widget, dx=0, dy=18, delay=0, duration=ENTER_MS):
    """Fade a widget in while it glides into its layout position."""
    if not animations_enabled() or not widget.isVisible():
        return
    end = widget.pos()
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)
    widget.move(end + QPoint(dx, dy))

    fade = QPropertyAnimation(effect, b"opacity")
    fade.setDuration(duration)
    fade.setEndValue(1.0)
    fade.setEasingCurve(QEasingCurve.OutCubic)

    glide = QPropertyAnimation(widget, b"pos")
    glide.setDuration(duration)
    glide.setEndValue(end)
    glide.setEasingCurve(QEasingCurve.OutQuart)

    group = QParallelAnimationGroup()
    group.addAnimation(fade)
    group.addAnimation(glide)

    sequence = QSequentialAnimationGroup(widget)
    if delay:
        sequence.addPause(delay)
    sequence.addAnimation(group)

    def done():
        widget.setGraphicsEffect(None)
        layout = widget.parentWidget().layout() if widget.parentWidget() else None
        if layout is not None:
            layout.invalidate()  # snap back to the layout in case it changed meanwhile

    sequence.finished.connect(done)
    _keep(widget, sequence)


def cascade(widgets, dx=0, dy=18, step=STAGGER_MS, duration=ENTER_MS):
    """Slide a list of widgets in one after the other, like cars leaving the pit lane."""
    for i, w in enumerate(widgets):
        slide_in(w, dx=dx, dy=dy, delay=i * step, duration=duration)


class AnimatedWindow:
    """Mixin for QMainWindow/QDialog: fades and lifts the window in on show, fades it out on close.

    Put it before the Qt class in the bases: class MyWindow(AnimatedWindow, QMainWindow).
    """

    enter_offset = 14

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "_shown_once", False) or not animations_enabled():
            return
        self._shown_once = True
        self.setWindowOpacity(0.0)
        fade = QPropertyAnimation(self, b"windowOpacity")
        fade.setDuration(ENTER_MS)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.OutCubic)
        _keep(self, fade)
        content = self._motion_content()
        if content is not None:
            # Wait for the first layout pass so the content has its final position.
            QTimer.singleShot(0, lambda: slide_in(content, dy=self.enter_offset))

    def _motion_content(self):
        central = getattr(self, "centralWidget", None)
        return central() if callable(central) else None

    def _fade_out(self, then):
        if getattr(self, "_fading_out", False):
            return
        self._fading_out = True
        fade = QPropertyAnimation(self, b"windowOpacity")
        fade.setDuration(EXIT_MS)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.InCubic)
        fade.finished.connect(then)
        _keep(self, fade)

    def defer_close_for_fade(self, event):
        """Ignore this close and fade out first; returns True when the close was deferred.

        Subclasses that override closeEvent call this first and return when it says True.
        """
        if getattr(self, "_closed_after_fade", False) or not animations_enabled() or not self.isVisible():
            return False
        event.ignore()

        def finish():
            self._closed_after_fade = True
            self.close()

        self._fade_out(finish)
        return True

    def closeEvent(self, event):
        if not self.defer_close_for_fade(event):
            super().closeEvent(event)

    def done(self, result):  # QDialog.accept()/reject() end here
        if getattr(self, "_closed_after_fade", False) or not animations_enabled():
            super().done(result)
            return

        def finish():
            self._closed_after_fade = True
            super(AnimatedWindow, self).done(result)

        self._fade_out(finish)


class SpeedLoader(QWidget):
    """Thin track with an F1-red streak racing across it, for waits of unknown length.

    The animation only runs while the widget is visible, so a hidden loader costs nothing.
    """

    def __init__(self, parent=None, height=4):
        super().__init__(parent)
        self.setFixedHeight(height)
        self._phase = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(950)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._anim.valueChanged.connect(self._tick)

    def _tick(self, value):
        self._phase = value
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        self._anim.start()

    def hideEvent(self, event):
        self._anim.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        radius = h / 2

        track = QPainterPath()
        track.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
        p.fillPath(track, QColor(255, 255, 255, 20))
        p.setClipPath(track)

        streak = w * 0.38
        head = -streak + (w + streak * 2) * self._phase
        grad = QLinearGradient(head - streak, 0, head, 0)
        grad.setColorAt(0.0, QColor(225, 6, 0, 0))
        grad.setColorAt(0.75, QColor(225, 6, 0, 210))
        grad.setColorAt(1.0, QColor(255, 120, 90, 255))
        p.fillRect(QRectF(head - streak, 0, streak, h), grad)
        p.end()


class LoadingDialog(AnimatedWindow, QDialog):
    """Frameless glass card shown while a session loads: a racing streak and a running clock,
    so a long download never looks like a frozen app."""

    def __init__(self, subtitle="", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowModality(Qt.ApplicationModal)
        self.setFixedWidth(380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 22, 26, 24)
        layout.setSpacing(8)
        title = QLabel("LOADING SESSION")
        title.setObjectName("sectionTitle")
        self._subtitle = QLabel(subtitle)
        self._subtitle.setObjectName("eventName")
        self._subtitle.setWordWrap(True)
        self._elapsed = QLabel("Fetching timing data…")
        self._elapsed.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(self._subtitle)
        layout.addSpacing(6)
        layout.addWidget(SpeedLoader())
        layout.addWidget(self._elapsed)

        self._seconds = 0
        self._stage = "Fetching timing data…"
        self._clock = QTimer(self)
        self._clock.timeout.connect(self._tick)
        self._clock.start(1000)

    def set_stage(self, text):
        self._stage = text
        self._elapsed.setText(f"{text}  {self._seconds}s" if self._seconds else text)

    def _tick(self):
        self._seconds += 1
        self._elapsed.setText(f"{self._stage}  {self._seconds}s")

    def _motion_content(self):
        return None

    def setVisible(self, visible):
        if visible and self.parentWidget() is not None:
            # Centre on the parent window before the native window is mapped.
            self.adjustSize()
            self.move(self.parentWidget().window().geometry().center() - self.rect().center())
        super().setVisible(visible)

    def done(self, result):
        self._clock.stop()
        super().done(result)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        card = QPainterPath()
        card.addRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 18, 18)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor("#1D1F27"))
        grad.setColorAt(1.0, QColor("#121319"))
        p.fillPath(card, grad)
        p.setPen(QColor(255, 255, 255, 30))
        p.drawPath(card)
        p.end()
