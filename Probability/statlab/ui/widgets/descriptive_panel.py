"""Descriptive statistics tab: pick a column, see full stats + histogram."""

from __future__ import annotations

import numpy as np
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core import descriptive
from core.models import ColumnKind
from ui.widgets.chart_canvas import ChartCanvas
from ui import style


class DescriptivePanel(QWidget):
    def __init__(self):
        super().__init__()
        self._df = None
        self._kinds: dict[str, ColumnKind] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        heading = QLabel("Descriptive statistics")
        heading.setObjectName("sectionHeading")
        layout.addWidget(heading)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Column:"))
        self.column_combo = QComboBox()
        self.column_combo.currentTextChanged.connect(self._on_column_changed)
        controls.addWidget(self.column_combo, stretch=1)

        controls.addWidget(QLabel("Bins:"))
        self.bin_spin = QSpinBox()
        self.bin_spin.setRange(5, 100)
        self.bin_spin.setValue(20)
        self.bin_spin.valueChanged.connect(self._refresh)
        controls.addWidget(self.bin_spin)

        layout.addLayout(controls)

        body = QHBoxLayout()
        body.setSpacing(16)

        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Statistic", "Value"])
        self.stats_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.stats_table.horizontalHeader().setStretchLastSection(True)
        body.addWidget(self.stats_table, stretch=1)

        self.chart = ChartCanvas(width=5, height=3.8)
        body.addWidget(self.chart, stretch=1)

        layout.addLayout(body, stretch=1)

        self.outlier_label = QLabel("")
        self.outlier_label.setObjectName("secondaryLabel")
        self.outlier_label.setWordWrap(True)
        layout.addWidget(self.outlier_label)

    def set_dataset(self, df, kinds: dict[str, ColumnKind]) -> None:
        self._df = df
        self._kinds = kinds
        self.column_combo.blockSignals(True)
        self.column_combo.clear()
        self.column_combo.addItems([str(c) for c in df.columns])
        self.column_combo.blockSignals(False)
        if df.shape[1] > 0:
            self._refresh()

    def _on_column_changed(self, _name: str) -> None:
        self._refresh()

    def _refresh(self) -> None:
        if self._df is None or self.column_combo.count() == 0:
            return
        col_name = self.column_combo.currentText()
        if not col_name:
            return
        kind = self._kinds.get(col_name, ColumnKind.UNKNOWN)
        series = self._df[col_name]

        self.stats_table.setRowCount(0)
        self.chart.clear()
        self.outlier_label.setText("")

        if kind == ColumnKind.NUMERIC:
            self._render_numeric(series, col_name)
        elif kind == ColumnKind.CATEGORICAL:
            self._render_categorical(series, col_name)
        else:
            self._add_row("Status", "Column has no usable values")

        self.chart.redraw()

    def _add_row(self, label: str, value: str) -> None:
        row = self.stats_table.rowCount()
        self.stats_table.insertRow(row)
        self.stats_table.setItem(row, 0, QTableWidgetItem(label))
        self.stats_table.setItem(row, 1, QTableWidgetItem(value))

    def _render_numeric(self, series, col_name: str) -> None:
        summary = descriptive.summarize_numeric(series, col_name)

        rows = [
            ("Count", f"{summary.count:,}"),
            ("Missing", f"{summary.missing:,}"),
            ("Mean", f"{summary.mean:.6g}"),
            ("Median", f"{summary.median:.6g}"),
            ("Mode", f"{summary.mode:.6g}" if summary.mode is not None else "n/a"),
            ("Std Dev", f"{summary.std_dev:.6g}"),
            ("Variance", f"{summary.variance:.6g}"),
            ("Minimum", f"{summary.minimum:.6g}"),
            ("Maximum", f"{summary.maximum:.6g}"),
            ("Range", f"{summary.range_:.6g}"),
            ("Q1 (25th pct)", f"{summary.q1:.6g}"),
            ("Q3 (75th pct)", f"{summary.q3:.6g}"),
            ("IQR", f"{summary.iqr:.6g}"),
            ("Skewness", f"{summary.skewness:.6g}"),
            ("Excess kurtosis", f"{summary.kurtosis:.6g}"),
            ("Std error of mean", f"{summary.sem:.6g}"),
            ("95% CI of mean", f"[{summary.ci_95_low:.6g}, {summary.ci_95_high:.6g}]"),
        ]
        for label, value in rows:
            self._add_row(label, value)

        counts, edges = descriptive.histogram_bins(series, self.bin_spin.value())
        ax = self.chart.figure.add_subplot(111)
        if len(counts) > 0:
            ax.bar(
                edges[:-1], counts, width=np.diff(edges),
                align="edge", color=style.ACCENT, edgecolor=style.BG_BASE,
            )
        ax.set_title(f"Distribution of {col_name}")
        ax.set_xlabel(col_name)
        ax.set_ylabel("Frequency")
        self.chart.style_axes(ax)

        outliers, lower, upper = descriptive.detect_outliers_iqr(series)
        if len(outliers) > 0:
            self.outlier_label.setText(
                f"{len(outliers)} outlier(s) outside [{lower:.4g}, {upper:.4g}] "
                f"(1.5 x IQR rule)."
            )
        else:
            self.outlier_label.setText("No outliers detected (1.5 x IQR rule).")

    def _render_categorical(self, series, col_name: str) -> None:
        summary = descriptive.summarize_categorical(series, col_name)

        rows = [
            ("Count", f"{summary.count:,}"),
            ("Missing", f"{summary.missing:,}"),
            ("Unique values", f"{summary.unique:,}"),
            ("Most frequent", str(summary.top_value)),
            ("Frequency of top value", f"{summary.top_frequency:,}"),
        ]
        for label, value in rows:
            self._add_row(label, value)

        top_items = list(summary.frequencies.items())[:15]
        ax = self.chart.figure.add_subplot(111)
        if top_items:
            labels = [str(k) for k, _ in top_items]
            values = [v for _, v in top_items]
            ax.barh(labels, values, color=style.ACCENT)
            ax.invert_yaxis()
        ax.set_title(f"Top categories in {col_name}")
        ax.set_xlabel("Count")
        self.chart.style_axes(ax)
