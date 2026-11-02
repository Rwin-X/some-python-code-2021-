"""A themed matplotlib FigureCanvas for embedding plots in Qt widgets."""

from __future__ import annotations

import matplotlib
matplotlib.use("QtAgg")

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from ui import style


class ChartCanvas(FigureCanvasQTAgg):
    """Embeddable matplotlib canvas pre-styled to match the dark palette."""

    def __init__(self, parent=None, width: float = 5, height: float = 3.5, dpi: int = 100):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.figure)
        self.setParent(parent)
        self._apply_theme()

    def _apply_theme(self) -> None:
        self.figure.patch.set_facecolor(style.BG_ELEVATED)

    def clear(self) -> None:
        self.figure.clear()
        self._apply_theme()

    def style_axes(self, ax) -> None:
        ax.set_facecolor(style.BG_SUNKEN)
        ax.tick_params(colors=style.TEXT_SECONDARY, labelsize=9)
        for spine in ax.spines.values():
            spine.set_color(style.BORDER)
        ax.xaxis.label.set_color(style.TEXT_SECONDARY)
        ax.yaxis.label.set_color(style.TEXT_SECONDARY)
        ax.title.set_color(style.TEXT_PRIMARY)
        ax.grid(True, color=style.BORDER, linewidth=0.5, alpha=0.6)

    def redraw(self) -> None:
        self.figure.tight_layout()
        self.draw()
