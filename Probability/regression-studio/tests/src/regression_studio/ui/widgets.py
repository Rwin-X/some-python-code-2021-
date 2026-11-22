"""Small reusable widgets."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import style


def section_label(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setObjectName("sectionLabel")
    return label


def labeled(text: str, widget: QWidget) -> QWidget:
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    caption = QLabel(text)
    caption.setObjectName("secondaryLabel")
    layout.addWidget(caption)
    layout.addWidget(widget)
    return box


class ArrowComboBox(QComboBox):
    """QComboBox with a procedurally drawn chevron instead of the platform arrow."""

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(style.TEXT_SECONDARY))
        pen.setWidthF(1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        cx, cy = self.width() - 16.0, self.height() / 2.0
        painter.drawPolyline(
            QPolygonF([QPointF(cx - 4, cy - 2), QPointF(cx, cy + 2), QPointF(cx + 4, cy - 2)])
        )


class MetricCard(QWidget):
    """A titled single-value tile for the dashboard row."""

    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("elevatedPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)
        self._title = QLabel(title)
        self._title.setObjectName("metricTitle")
        self._value = QLabel("-")
        self._value.setObjectName("metricValue")
        layout.addWidget(self._title)
        layout.addWidget(self._value)

    def set_value(self, text: str) -> None:
        self._value.setText(text)


def make_readonly_table(headers: list[str], compact: bool = False) -> QTableWidget:
    """Read-only table. `compact` sizes columns to content and stretches the last."""
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    header = table.horizontalHeader()
    if compact:
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
    else:
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    return table


def fill_table(table: QTableWidget, rows: list[list[str]], accent_first: bool = False) -> None:
    table.setRowCount(len(rows))
    for i, row in enumerate(rows):
        for j, text in enumerate(row):
            item = QTableWidgetItem(text)
            align = Qt.AlignmentFlag.AlignLeft if j == 0 else Qt.AlignmentFlag.AlignRight
            item.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
            if accent_first and i == 0 and j == 0:
                item.setForeground(QColor(style.ACCENT))
            table.setItem(i, j, item)
