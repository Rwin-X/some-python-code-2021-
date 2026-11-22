"""Custom frameless window chrome: title bar, drag-to-move, window controls."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QPushButton, QWidget

from . import style


class LogoIcon(QWidget):
    """Three data points and a fit line, drawn procedurally."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(20, 20)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(style.ACCENT)
        pen = QPen(color)
        pen.setWidthF(1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(QPointF(3, 16), QPointF(17, 4))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        for x, y in ((5, 11), (10, 11.5), (15, 6)):
            painter.drawEllipse(QPointF(x, y), 1.8, 1.8)


class WindowControlButton(QPushButton):
    """Minimize / maximize / restore / close glyph button."""

    def __init__(self, glyph: str) -> None:
        super().__init__()
        self._glyph = glyph
        self.setFixedSize(28, 28)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_glyph(self, glyph: str) -> None:
        self._glyph = glyph
        self.update()

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        hovered = self.underMouse()
        is_close = self._glyph == "close"
        if hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#3a1f1d") if is_close else QColor(style.BG_HOVER))
            painter.drawRoundedRect(QRectF(self.rect()), 6, 6)
        if is_close:
            color = QColor("#e07a70" if hovered else style.DANGER)
        else:
            color = QColor(style.TEXT_PRIMARY if hovered else style.TEXT_SECONDARY)
        pen = QPen(color)
        pen.setWidthF(1.2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        cx, cy, s = self.width() / 2.0, self.height() / 2.0, 5.0
        if self._glyph == "minimize":
            painter.drawLine(QPointF(cx - s, cy), QPointF(cx + s, cy))
        elif self._glyph == "maximize":
            painter.drawRect(QRectF(cx - s, cy - s, 2 * s, 2 * s))
        elif self._glyph == "restore":
            painter.drawRect(QRectF(cx - s + 2, cy - s, 2 * s - 2, 2 * s - 2))
            painter.drawRect(QRectF(cx - s, cy - s + 2, 2 * s - 2, 2 * s - 2))
        else:
            painter.drawLine(QPointF(cx - s, cy - s), QPointF(cx + s, cy + s))
            painter.drawLine(QPointF(cx - s, cy + s), QPointF(cx + s, cy - s))


class TitleBar(QWidget):
    BAR_HEIGHT = 36

    def __init__(self, window: QMainWindow, title: str) -> None:
        super().__init__()
        self._window = window
        self._drag_offset: QPoint | None = None
        self.setObjectName("titleBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(self.BAR_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(8)
        layout.addWidget(LogoIcon())
        layout.addWidget(QLabel(title))
        layout.addStretch()

        self.minimize_btn = WindowControlButton("minimize")
        self.maximize_btn = WindowControlButton("maximize")
        self.close_btn = WindowControlButton("close")
        self.minimize_btn.clicked.connect(window.showMinimized)
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        self.close_btn.clicked.connect(window.close)
        for button in (self.minimize_btn, self.maximize_btn, self.close_btn):
            layout.addWidget(button)

    def toggle_maximize(self) -> None:
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()
        self.sync_maximize_glyph()

    def sync_maximize_glyph(self) -> None:
        self.maximize_btn.set_glyph("restore" if self._window.isMaximized() else "maximize")

    # Drag-to-move: ask the window system first (works on Wayland), fall back
    # to manual offset tracking where that is unavailable.
    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        handle = self._window.windowHandle()
        if handle is not None and handle.startSystemMove():
            return
        self._drag_offset = event.globalPosition().toPoint() - self._window.pos()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None

    def mouseDoubleClickEvent(self, event) -> None:
        self.toggle_maximize()
