"""Cash flow diagram drawn with QPainter: time axis, arrows up (inflow) and down (outflow)."""
import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QWidget

from ui.format import fmt
from ui.style import (ACCENT, BG_SUNKEN, BORDER, DANGER, TEXT_SECONDARY,
                      TEXT_TERTIARY)


class CashFlowDiagram(QWidget):
    def __init__(self, height: int = 150):
        super().__init__()
        self.setFixedHeight(height)
        self._flows: list[float] = []
        self._title = ""
        self._caption = ""

    def set_flows(self, flows, title: str = "", caption: str = "") -> None:
        self._flows, self._title, self._caption = list(flows), title, caption
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(BORDER), 1))
        p.setBrush(QColor(BG_SUNKEN))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)
        flows = self._flows
        if len(flows) < 2:
            return
        n = len(flows) - 1
        w, h = self.width(), self.height()
        plot = QRectF(30, 48, w - 60, h - 48 - 34)
        vmax, vmin = max(max(flows), 0.0), min(min(flows), 0.0)
        if vmax == vmin:
            vmax = 1.0
        y = lambda v: plot.top() + (vmax - v) / (vmax - vmin) * plot.height()
        x = lambda t: plot.left() + plot.width() * t / n
        base = y(0.0)

        p.setPen(QPen(QColor(TEXT_TERTIARY), 1.2))
        p.drawLine(QPointF(plot.left() - 10, base), QPointF(plot.right() + 10, base))
        step = max(1, math.ceil(n / 12))
        for t in range(n + 1):
            p.setPen(QPen(QColor(TEXT_TERTIARY), 1))
            p.drawLine(QPointF(x(t), base - 3), QPointF(x(t), base + 3))
            if t % step == 0 or t == n:
                p.setPen(QColor(TEXT_SECONDARY))
                p.drawText(QRectF(x(t) - 20, h - 24, 40, 16), int(Qt.AlignmentFlag.AlignCenter), str(t))

        show_labels = n <= 10
        for t, v in enumerate(flows):
            if abs(v) < 1e-9:
                continue
            color = QColor(ACCENT if v > 0 else DANGER)
            tip = y(v)
            p.setPen(QPen(color, 1.8 if n <= 20 else 1.2))
            p.drawLine(QPointF(x(t), base), QPointF(x(t), tip))
            d = 7 if v > 0 else -7
            p.setBrush(color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPolygon(QPolygonF([QPointF(x(t), tip), QPointF(x(t) - 4, tip + d), QPointF(x(t) + 4, tip + d)]))
            if show_labels:
                p.setPen(QColor(TEXT_SECONDARY))
                if v > 0:  # amount above the arrow tip
                    p.drawText(QRectF(x(t) - 40, tip - 17, 80, 14), int(Qt.AlignmentFlag.AlignCenter), fmt(v, 0))
                else:      # amount beside the arrow so it never meets the time labels
                    p.drawText(QRectF(x(t) + 7, (base + tip) / 2 - 7, 90, 14),
                               int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), fmt(v, 0))

        p.setPen(QColor(TEXT_SECONDARY))
        p.drawText(QRectF(12, 6, w / 2, 18), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), self._title)
        p.drawText(QRectF(w / 2, 6, w / 2 - 12, 18), int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), self._caption)
