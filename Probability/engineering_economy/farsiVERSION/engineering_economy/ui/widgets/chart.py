"""NPV profile chart drawn with QPainter (no plotting dependency)."""
import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QWidget

from ui.format import fmt
from ui.style import ACCENT, BG_SUNKEN, BORDER, TEXT_SECONDARY, TEXT_TERTIARY


class ProfileChart(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(190)
        self._data = None

    def set_data(self, rates, values, marr, roots) -> None:
        self._data = (list(rates), list(values), marr, list(roots))
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(QColor(BORDER), 1))
        p.setBrush(QColor(BG_SUNKEN))
        p.drawRoundedRect(box, 8, 8)
        if not self._data:
            return
        rates, values, marr, roots = self._data
        pts = [(r, v) for r, v in zip(rates, values) if math.isfinite(v)]
        if len(pts) < 2:
            return
        left, right, top, bottom = 64, 18, 24, 26
        plot = QRectF(left, top, self.width() - left - right, self.height() - top - bottom)
        rmax = rates[-1]
        vmin = min([v for _, v in pts] + [0.0])
        vmax = max([v for _, v in pts] + [0.0])
        if vmax == vmin:
            vmax += 1.0
        x = lambda r: plot.left() + plot.width() * r / rmax
        y = lambda v: plot.bottom() - plot.height() * (v - vmin) / (vmax - vmin)

        p.setPen(QPen(QColor(BORDER), 1))
        p.drawLine(QPointF(plot.left(), y(0)), QPointF(plot.right(), y(0)))
        if marr <= rmax:
            p.setPen(QPen(QColor(TEXT_TERTIARY), 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(x(marr), plot.top()), QPointF(x(marr), plot.bottom()))
            p.setPen(QColor(TEXT_SECONDARY))
            p.drawText(QPointF(x(marr) + 4, plot.top() + 10), f"MARR {marr * 100:.1f}%")
        p.setPen(QPen(QColor(ACCENT), 2))
        p.drawPolyline(QPolygonF([QPointF(x(r), y(v)) for r, v in pts]))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(ACCENT))
        for r in roots:
            if r <= rmax:
                p.drawEllipse(QPointF(x(r), y(0)), 4, 4)
        p.setPen(QColor(TEXT_SECONDARY))
        p.drawText(QPointF(plot.left(), self.height() - 8), "0%")
        p.drawText(QPointF(plot.right() - 30, self.height() - 8), f"{rmax * 100:.0f}%")
        p.drawText(QRectF(4, plot.top() - 8, left - 10, 16),
                   int(Qt.AlignmentFlag.AlignRight), fmt(vmax, 0))
        p.drawText(QRectF(4, plot.bottom() - 8, left - 10, 16),
                   int(Qt.AlignmentFlag.AlignRight), fmt(vmin, 0))
