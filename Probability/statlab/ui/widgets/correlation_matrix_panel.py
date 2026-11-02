"""Correlation matrix tab: heatmap across all numeric columns at once."""

from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from core import inferential
from core.models import ColumnKind
from ui.widgets.chart_canvas import ChartCanvas
from ui import style


class CorrelationMatrixPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._df = None
        self._kinds: dict[str, ColumnKind] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        heading = QLabel("Correlation matrix")
        heading.setObjectName("sectionHeading")
        layout.addWidget(heading)

        self.info_label = QLabel("Load a dataset with at least two numeric columns.")
        self.info_label.setObjectName("secondaryLabel")
        layout.addWidget(self.info_label)

        self.chart = ChartCanvas(width=6, height=6)
        layout.addWidget(self.chart, stretch=1)

    def set_dataset(self, df, kinds: dict[str, ColumnKind]) -> None:
        self._df = df
        self._kinds = kinds
        numeric_cols = [c for c, k in kinds.items() if k == ColumnKind.NUMERIC]

        self.chart.clear()
        if len(numeric_cols) < 2:
            self.info_label.setText("Need at least two numeric columns to compute a correlation matrix.")
            self.chart.redraw()
            return

        self.info_label.setText(f"Pearson correlation across {len(numeric_cols)} numeric columns.")
        matrix = inferential.correlation_matrix(df, numeric_cols)

        ax = self.chart.figure.add_subplot(111)
        im = ax.imshow(matrix.values, cmap="RdYlGn", vmin=-1, vmax=1, aspect="auto")
        ax.set_xticks(range(len(matrix.columns)))
        ax.set_xticklabels(matrix.columns, rotation=45, ha="right", fontsize=8)
        ax.set_yticks(range(len(matrix.index)))
        ax.set_yticklabels(matrix.index, fontsize=8)

        for i in range(len(matrix.index)):
            for j in range(len(matrix.columns)):
                value = matrix.values[i, j]
                ax.text(
                    j, i, f"{value:.2f}", ha="center", va="center",
                    color="#0c0c0e" if abs(value) > 0.5 else style.TEXT_PRIMARY,
                    fontsize=7,
                )

        self.chart.style_axes(ax)
        self.chart.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        self.chart.redraw()
