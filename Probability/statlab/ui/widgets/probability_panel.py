"""Probability distributions tab: PDF/PMF/CDF plots and probability queries."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core import distributions as dist
from ui.widgets.chart_canvas import ChartCanvas
from ui import style


class ProbabilityPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._param_spins: dict[str, QDoubleSpinBox] = {}
        self._build_ui()
        self._on_distribution_changed(self.dist_combo.currentText())

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        heading = QLabel("Probability distributions")
        heading.setObjectName("sectionHeading")
        layout.addWidget(heading)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Distribution:"))
        self.dist_combo = QComboBox()
        self.dist_combo.addItems(dist.DISTRIBUTION_NAMES)
        self.dist_combo.currentTextChanged.connect(self._on_distribution_changed)
        top_row.addWidget(self.dist_combo)
        top_row.addStretch()
        layout.addLayout(top_row)

        body = QHBoxLayout()
        body.setSpacing(16)

        left_col = QVBoxLayout()
        self.params_form = QFormLayout()
        left_col.addLayout(self.params_form)

        self.mean_label = QLabel("")
        self.mean_label.setObjectName("secondaryLabel")
        left_col.addWidget(self.mean_label)

        left_col.addSpacing(8)
        left_col.addWidget(_divider_label("Probability query"))

        query_form = QFormLayout()
        self.query_low = QDoubleSpinBox()
        self.query_low.setRange(-1e9, 1e9)
        self.query_low.setDecimals(4)
        self.query_high = QDoubleSpinBox()
        self.query_high.setRange(-1e9, 1e9)
        self.query_high.setDecimals(4)
        self.query_high.setValue(1.0)
        query_form.addRow("Lower bound (a):", self.query_low)
        query_form.addRow("Upper bound (b):", self.query_high)
        left_col.addLayout(query_form)

        self.compute_btn = QPushButton("Compute P(a <= X <= b)")
        self.compute_btn.setObjectName("primaryAction")
        self.compute_btn.clicked.connect(self._compute_probability)
        left_col.addWidget(self.compute_btn)

        self.result_grid = QGridLayout()
        self._result_labels: dict[str, QLabel] = {}
        for i, key in enumerate(["between", "at_most", "at_least", "exact"]):
            self._result_labels[key] = QLabel("-")
            self._result_labels[key].setObjectName("monoLabel")
        self.result_grid.addWidget(QLabel("P(a <= X <= b):"), 0, 0)
        self.result_grid.addWidget(self._result_labels["between"], 0, 1)
        self.result_grid.addWidget(QLabel("P(X <= b):"), 1, 0)
        self.result_grid.addWidget(self._result_labels["at_most"], 1, 1)
        self.result_grid.addWidget(QLabel("P(X >= a):"), 2, 0)
        self.result_grid.addWidget(self._result_labels["at_least"], 2, 1)
        self.result_grid.addWidget(QLabel("P(X = a) [discrete only]:"), 3, 0)
        self.result_grid.addWidget(self._result_labels["exact"], 3, 1)
        left_col.addLayout(self.result_grid)
        left_col.addStretch()

        body.addLayout(left_col, stretch=1)

        self.chart = ChartCanvas(width=5.5, height=5)
        body.addWidget(self.chart, stretch=1)

        layout.addLayout(body, stretch=1)

        # Recompute curve whenever a parameter changes.
        self.dist_combo.currentTextChanged.connect(lambda _: self._redraw_curve())

    def _on_distribution_changed(self, distribution: str) -> None:
        while self.params_form.rowCount() > 0:
            self.params_form.removeRow(0)
        self._param_spins.clear()

        for key, label, default, is_integer in dist.DISTRIBUTION_PARAMS[distribution]:
            spin = QDoubleSpinBox()
            spin.setRange(-1e6, 1e6)
            spin.setDecimals(0 if is_integer else 4)
            spin.setSingleStep(1.0 if is_integer else 0.1)
            spin.setValue(default)
            spin.valueChanged.connect(self._redraw_curve)
            self._param_spins[key] = spin
            self.params_form.addRow(label + ":", spin)

        self._redraw_curve()

    def _current_params(self) -> dict[str, float]:
        return {key: spin.value() for key, spin in self._param_spins.items()}

    def _redraw_curve(self) -> None:
        distribution = self.dist_combo.currentText()
        params = self._current_params()
        if distribution == "uniform" and params.get("high", 1) <= params.get("low", 0):
            return

        try:
            curve = dist.compute_curve(distribution, params)
            mean, var = dist.mean_and_variance(distribution, params)
        except Exception:
            return

        self.mean_label.setText(f"Mean = {mean:.4g}    Variance = {var:.4g}    Std Dev = {var ** 0.5:.4g}")

        self.chart.clear()
        is_discrete = distribution in dist.DISCRETE_DISTRIBUTIONS

        ax1 = self.chart.figure.add_subplot(211)
        if is_discrete:
            ax1.bar(curve.x, curve.pdf_or_pmf, color=style.ACCENT, width=0.8)
            ax1.set_ylabel("PMF")
        else:
            ax1.plot(curve.x, curve.pdf_or_pmf, color=style.ACCENT, linewidth=1.8)
            ax1.fill_between(curve.x, curve.pdf_or_pmf, color=style.ACCENT, alpha=0.15)
            ax1.set_ylabel("PDF")
        ax1.set_title(f"{distribution.capitalize()} distribution")
        self.chart.style_axes(ax1)

        ax2 = self.chart.figure.add_subplot(212)
        ax2.plot(curve.x, curve.cdf, color=style.TEXT_PRIMARY, linewidth=1.5)
        ax2.set_ylabel("CDF")
        ax2.set_xlabel("x")
        self.chart.style_axes(ax2)

        self.chart.redraw()

    def _compute_probability(self) -> None:
        distribution = self.dist_combo.currentText()
        params = self._current_params()
        a = self.query_low.value()
        b = self.query_high.value()

        try:
            between = dist.probability_between(distribution, params, a, b)
            at_most = dist.probability_at_most(distribution, params, b)
            at_least = dist.probability_at_least(distribution, params, a)
            exact = dist.probability_exact(distribution, params, a)
        except Exception as exc:
            self._result_labels["between"].setText(f"Error: {exc}")
            return

        self._result_labels["between"].setText(f"{between:.6f}")
        self._result_labels["at_most"].setText(f"{at_most:.6f}")
        self._result_labels["at_least"].setText(f"{at_least:.6f}")
        self._result_labels["exact"].setText(f"{exact:.6f}" if exact is not None else "n/a (continuous)")


def _divider_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("secondaryLabel")
    return label
