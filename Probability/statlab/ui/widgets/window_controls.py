"""Procedurally drawn minimize/maximize/close glyph buttons."""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QPushButton

from ui import style


class WindowControlButton(QPushButton):
    """Minimal glyph button for minimize/maximize/close, drawn with
    QPainter rather than platform icons, matching the app palette."""

    def __init__(self, glyph: str):
        super().__init__()
        self._glyph = glyph
        self.setFixedSize(28, 28)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if glyph == "close":
            self.setObjectName("closeControl")

    def set_glyph(self, glyph: str) -> None:
        self._glyph = glyph
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override name)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        base = QColor(style.TEXT_SECONDARY)
        close_base = QColor(style.DANGER)
        hover_normal = QColor(style.TEXT_PRIMARY)
        hover_close = QColor("#e07a70")

        if self._glyph == "close":
            color = hover_close if self.underMouse() else close_base
        else:
            color = hover_normal if self.underMouse() else base

        painter.setPen(color)
        rect = QRectF(0, 0, self.width(), self.height())
        cx, cy = rect.center().x(), rect.center().y()
        size = 5

        if self._glyph == "minimize":
            painter.drawLine(int(cx - size), int(cy), int(cx + size), int(cy))
        elif self._glyph == "maximize":
            painter.drawRect(int(cx - size), int(cy - size), size * 2, size * 2)
        elif self._glyph == "restore":
            painter.drawRect(int(cx - size + 2), int(cy - size), size * 2 - 2, size * 2 - 2)
            painter.drawRect(int(cx - size), int(cy - size + 2), size * 2 - 2, size * 2 - 2)
        elif self._glyph == "close":
            painter.drawLine(int(cx - size), int(cy - size), int(cx + size), int(cy + size))
            painter.drawLine(int(cx - size), int(cy + size), int(cx + size), int(cy - size))
