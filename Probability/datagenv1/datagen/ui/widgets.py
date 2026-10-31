"""Reusable widgets: glyph buttons, title bar, combo box, field row."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QWidget,
)

from ..core.generators import TYPE_BY_KEY, TYPES
from ..core.models import FieldSpec
from . import style


class GlyphButton(QPushButton):
    """Small button whose glyph is drawn with QPainter (no image assets)."""

    def __init__(self, glyph: str, size: int = 28):
        super().__init__()
        self._glyph = glyph
        self.setFixedSize(size, size)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_glyph(self, glyph: str) -> None:
        self._glyph = glyph
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        hovered = self.underMouse()
        if hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(style.BG_HOVER))
            painter.drawRoundedRect(QRectF(self.rect()), 6, 6)

        if self._glyph == "close":
            color = QColor("#e07a70" if hovered else style.DANGER)
        elif self._glyph == "remove":
            color = QColor(style.TEXT_PRIMARY if hovered else style.TEXT_TERTIARY)
        else:
            color = QColor(style.TEXT_PRIMARY if hovered else style.TEXT_SECONDARY)

        pen = QPen(color, 1.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        cx, cy = self.width() / 2, self.height() / 2
        r = 5.0

        if self._glyph == "minimize":
            painter.drawLine(QPointF(cx - r, cy), QPointF(cx + r, cy))
        elif self._glyph == "maximize":
            painter.drawRect(QRectF(cx - r, cy - r, 2 * r, 2 * r))
        elif self._glyph == "restore":
            painter.drawRect(QRectF(cx - r + 2, cy - r, 2 * r - 2, 2 * r - 2))
            painter.drawRect(QRectF(cx - r, cy - r + 2, 2 * r - 2, 2 * r - 2))
        elif self._glyph in ("close", "remove"):
            painter.drawLine(QPointF(cx - r, cy - r), QPointF(cx + r, cy + r))
            painter.drawLine(QPointF(cx - r, cy + r), QPointF(cx + r, cy - r))


class TitleBar(QWidget):
    """Slim custom title bar: drag-to-move, minimize/maximize/close."""

    BAR_HEIGHT = 36

    def __init__(self, window: QMainWindow, title: str):
        super().__init__()
        self._window = window
        self._drag_offset = None

        self.setObjectName("titleBar")
        self.setFixedHeight(self.BAR_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 8, 0)
        layout.setSpacing(2)
        layout.addWidget(QLabel(title))
        layout.addStretch()

        self.minimize_btn = GlyphButton("minimize")
        self.maximize_btn = GlyphButton("maximize")
        self.close_btn = GlyphButton("close")

        self.minimize_btn.clicked.connect(self._window.showMinimized)
        self.maximize_btn.clicked.connect(self._toggle_maximize)
        self.close_btn.clicked.connect(self._window.close)

        for button in (self.minimize_btn, self.maximize_btn, self.close_btn):
            layout.addWidget(button)

    def _toggle_maximize(self) -> None:
        if self._window.isMaximized():
            self._window.showNormal()
            self.maximize_btn.set_glyph("maximize")
        else:
            self._window.showMaximized()
            self.maximize_btn.set_glyph("restore")

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
        self._toggle_maximize()


class TypeCombo(QComboBox):
    """Combo box with a painted chevron and no accidental wheel changes."""

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(style.TEXT_TERTIARY if not self.isEnabled() else style.TEXT_SECONDARY)
        pen = QPen(color, 1.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        x, y = self.width() - 16.0, self.height() / 2
        painter.drawLine(QPointF(x - 4, y - 2), QPointF(x, y + 2))
        painter.drawLine(QPointF(x, y + 2), QPointF(x + 4, y - 2))

    def wheelEvent(self, event) -> None:
        event.ignore()


class FieldRow(QWidget):
    """One editable field definition: name, type, parameters, remove."""

    COLUMN_STRETCH = (3, 3, 4)
    REMOVE_SIZE = 28
    SPACING = 8

    remove_requested = pyqtSignal(object)

    def __init__(self, name: str = "", type_key: str = "word", params: str = ""):
        super().__init__()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self.SPACING)

        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("field_name")

        self.type_combo = TypeCombo()
        for spec in TYPES:
            self.type_combo.addItem(spec.label, spec.key)
        self.type_combo.setCurrentIndex(max(0, self.type_combo.findData(type_key)))

        self.params_edit = QLineEdit(params)

        self.remove_btn = GlyphButton("remove", self.REMOVE_SIZE)
        self.remove_btn.setToolTip("Remove field")
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))

        for widget, stretch in zip(
            (self.name_edit, self.type_combo, self.params_edit), self.COLUMN_STRETCH
        ):
            layout.addWidget(widget, stretch)
        layout.addWidget(self.remove_btn)

        self.type_combo.currentIndexChanged.connect(self._sync_params)
        self._sync_params()

    def _sync_params(self) -> None:
        spec = TYPE_BY_KEY[self.type_combo.currentData()]
        has_params = bool(spec.hint)
        self.params_edit.setEnabled(has_params)
        self.params_edit.setPlaceholderText(spec.hint)
        if not has_params:
            self.params_edit.clear()

    def to_spec(self) -> FieldSpec:
        return FieldSpec(
            name=self.name_edit.text().strip(),
            type_key=self.type_combo.currentData(),
            params=self.params_edit.text().strip(),
        )
