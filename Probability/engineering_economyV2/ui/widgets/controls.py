"""Small custom controls: combo with a drawn chevron, and window control glyph buttons."""
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QComboBox, QPushButton

from ui.style import TEXT_PRIMARY, TEXT_SECONDARY, DANGER


class Combo(QComboBox):
    """QComboBox with a QPainter chevron (QSS removes the native arrow)."""

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(TEXT_SECONDARY), 1.5))
        cx, cy = self.width() - 16, self.height() / 2
        p.drawPolyline([QPointF(cx - 4, cy - 2), QPointF(cx, cy + 2), QPointF(cx + 4, cy - 2)])


class WindowControlButton(QPushButton):
    """Minimize / maximize / restore / close glyph drawn with QPainter."""

    def __init__(self, glyph: str):
        super().__init__()
        self._glyph = glyph
        self.setFixedSize(28, 28)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("background: transparent; border: none;")

    def set_glyph(self, glyph: str) -> None:
        self._glyph = glyph
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._glyph == "close":
            color = QColor(DANGER if not self.underMouse() else "#e07a70")
        else:
            color = QColor(TEXT_PRIMARY if self.underMouse() else TEXT_SECONDARY)
        p.setPen(QPen(color, 1.3))
        r = QRectF(self.rect())
        cx, cy, s = r.center().x(), r.center().y(), 5
        if self._glyph == "minimize":
            p.drawLine(QPointF(cx - s, cy), QPointF(cx + s, cy))
        elif self._glyph == "maximize":
            p.drawRect(QRectF(cx - s, cy - s, 2 * s, 2 * s))
        elif self._glyph == "restore":
            p.drawRect(QRectF(cx - s + 2, cy - s, 2 * s - 2, 2 * s - 2))
            p.drawRect(QRectF(cx - s, cy - s + 2, 2 * s - 2, 2 * s - 2))
        else:
            p.drawLine(QPointF(cx - s, cy - s), QPointF(cx + s, cy + s))
            p.drawLine(QPointF(cx - s, cy + s), QPointF(cx + s, cy - s))
