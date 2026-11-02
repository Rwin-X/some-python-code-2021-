"""Inferential statistics tab: hypothesis tests and relationships between columns."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core import inferential
from core.models import ColumnKind
from ui.widgets.chart_canvas import ChartCanvas
from ui import style

TEST_CORRELATION = "Correlation (Pearson + Spearman)"
TEST_REGRESSION = "Simple linear regression"
TEST_ONE_SAMPLE_T = "One-sample t-test"
TEST_TWO_SAMPLE_T = "Two-sample t-test (independent)"
TEST_PAIRED_T = "Paired t-test"
TEST_CHI_SQUARE = "Chi-square test of independence"
TEST_ANOVA = "One-way ANOVA"

ALL_TESTS = [
    TEST_CORRELATION,
    TEST_REGRESSION,
    TEST_ONE_SAMPLE_T,
    TEST_TWO_SAMPLE_T,
    TEST_PAIRED_T,
    TEST_CHI_SQUARE,
    TEST_ANOVA,
]


class InferentialPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._df = None
        self._kinds: dict[str, ColumnKind] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        heading = QLabel("Inferential statistics")
        heading.setObjectName("sectionHeading")
        layout.addWidget(heading)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Test:"))
        self.test_combo = QComboBox()
        self.test_combo.addItems(ALL_TESTS)
        self.test_combo.currentTextChanged.connect(self._on_test_changed)
        top_row.addWidget(self.test_combo, stretch=1)
        layout.addLayout(top_row)

        body = QHBoxLayout()
        body.setSpacing(16)

        left_col = QVBoxLayout()

        self.col_a_combo = QComboBox()
        self.col_b_combo = QComboBox()
        self.group_combo = QComboBox()
        self.popmean_spin = QDoubleSpinBox()
        self.popmean_spin.setRange(-1e9, 1e9)
        self.popmean_spin.setDecimals(4)

        self.form = QFormLayout()
        left_col.addLayout(self.form)

        self.run_btn = QPushButton("Run test")
        self.run_btn.setObjectName("primaryAction")
        self.run_btn.clicked.connect(self._run_test)
        left_col.addWidget(self.run_btn)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        left_col.addWidget(self.result_text, stretch=1)

        body.addLayout(left_col, stretch=1)

        self.chart = ChartCanvas(width=5, height=4)
        body.addWidget(self.chart, stretch=1)

        layout.addLayout(body, stretch=1)

        self._on_test_changed(self.test_combo.currentText())

    def set_dataset(self, df, kinds: dict[str, ColumnKind]) -> None:
        self._df = df
        self._kinds = kinds
        self._on_test_changed(self.test_combo.currentText())

    def _numeric_columns(self) -> list[str]:
        return [c for c, k in self._kinds.items() if k == ColumnKind.NUMERIC] if self._df is not None else []

    def _categorical_columns(self) -> list[str]:
        return [c for c, k in self._kinds.items() if k == ColumnKind.CATEGORICAL] if self._df is not None else []

    def _all_columns(self) -> list[str]:
        return list(self._df.columns.astype(str)) if self._df is not None else []

    def _clear_form(self) -> None:
        while self.form.rowCount() > 0:
            self.form.removeRow(0)

    def _on_test_changed(self, test_name: str) -> None:
        self._clear_form()
        numeric = self._numeric_columns()
        categorical = self._categorical_columns()
        all_cols = self._all_columns()

        def fresh_combo(items: list[str]) -> QComboBox:
            combo = QComboBox()
            combo.addItems(items)
            return combo

        if test_name in (TEST_CORRELATION, TEST_REGRESSION):
            self.col_a_combo = fresh_combo(numeric)
            self.col_b_combo = fresh_combo(numeric)
            self.form.addRow("Column X:", self.col_a_combo)
            self.form.addRow("Column Y:", self.col_b_combo)

        elif test_name == TEST_ONE_SAMPLE_T:
            self.col_a_combo = fresh_combo(numeric)
            self.form.addRow("Column:", self.col_a_combo)
            self.popmean_spin.setValue(0.0)
            self.form.addRow("Hypothesized mean:", self.popmean_spin)

        elif test_name in (TEST_TWO_SAMPLE_T, TEST_PAIRED_T):
            self.col_a_combo = fresh_combo(numeric)
            self.col_b_combo = fresh_combo(numeric)
            self.form.addRow("Column A:", self.col_a_combo)
            self.form.addRow("Column B:", self.col_b_combo)

        elif test_name == TEST_CHI_SQUARE:
            self.col_a_combo = fresh_combo(categorical or all_cols)
            self.col_b_combo = fresh_combo(categorical or all_cols)
            self.form.addRow("Column A (categorical):", self.col_a_combo)
            self.form.addRow("Column B (categorical):", self.col_b_combo)

        elif test_name == TEST_ANOVA:
            self.col_a_combo = fresh_combo(numeric)
            self.group_combo = fresh_combo(categorical or all_cols)
            self.form.addRow("Value column (numeric):", self.col_a_combo)
            self.form.addRow("Group column (categorical):", self.group_combo)

        self.result_text.clear()
        self.chart.clear()
        self.chart.redraw()

    def _run_test(self) -> None:
        if self._df is None:
            self.result_text.setPlainText("Load a dataset first.")
            return

        test_name = self.test_combo.currentText()
        try:
            if test_name == TEST_CORRELATION:
                self._run_correlation()
            elif test_name == TEST_REGRESSION:
                self._run_regression()
            elif test_name == TEST_ONE_SAMPLE_T:
                self._run_one_sample_t()
            elif test_name == TEST_TWO_SAMPLE_T:
                self._run_two_sample_t()
            elif test_name == TEST_PAIRED_T:
                self._run_paired_t()
            elif test_name == TEST_CHI_SQUARE:
                self._run_chi_square()
            elif test_name == TEST_ANOVA:
                self._run_anova()
        except Exception as exc:
            self.result_text.setPlainText(f"Could not run test: {exc}")

    def _run_correlation(self) -> None:
        x_name = self.col_a_combo.currentText()
        y_name = self.col_b_combo.currentText()
        result = inferential.correlation(self._df[x_name], self._df[y_name], x_name, y_name)

        text = (
            f"Pearson r = {result.pearson_r:.4f}   (p = {result.pearson_p:.4g})\n"
            f"Spearman rho = {result.spearman_r:.4f}   (p = {result.spearman_p:.4g})\n"
            f"n = {result.n}\n\n"
            f"{inferential.interpret_p_value(result.pearson_p)}"
        )
        self.result_text.setPlainText(text)

        self.chart.clear()
        ax = self.chart.figure.add_subplot(111)
        from core.data_loader import coerce_numeric
        x = coerce_numeric(self._df[x_name])
        y = coerce_numeric(self._df[y_name])
        ax.scatter(x, y, color=style.ACCENT, s=14, alpha=0.7)
        ax.set_xlabel(x_name)
        ax.set_ylabel(y_name)
        ax.set_title(f"{x_name} vs {y_name}")
        self.chart.style_axes(ax)
        self.chart.redraw()

    def _run_regression(self) -> None:
        x_name = self.col_a_combo.currentText()
        y_name = self.col_b_combo.currentText()
        result = inferential.linear_regression(self._df[x_name], self._df[y_name])

        text = (
            f"y = {result.slope:.4f} * x + {result.intercept:.4f}\n"
            f"R^2 = {result.r_squared:.4f}   (r = {result.r_value:.4f})\n"
            f"p = {result.p_value:.4g}   std err of slope = {result.std_err:.4g}\n\n"
            f"{inferential.interpret_p_value(result.p_value)}"
        )
        self.result_text.setPlainText(text)

        self.chart.clear()
        ax = self.chart.figure.add_subplot(111)
        from core.data_loader import coerce_numeric
        import numpy as np
        x = coerce_numeric(self._df[x_name]).dropna()
        y = coerce_numeric(self._df[y_name]).dropna()
        ax.scatter(x, y, color=style.ACCENT, s=14, alpha=0.6)
        if len(x) > 1:
            xs = np.linspace(x.min(), x.max(), 100)
            ys = result.slope * xs + result.intercept
            ax.plot(xs, ys, color=style.TEXT_PRIMARY, linewidth=1.8)
        ax.set_xlabel(x_name)
        ax.set_ylabel(y_name)
        ax.set_title("Linear regression fit")
        self.chart.style_axes(ax)
        self.chart.redraw()

    def _run_one_sample_t(self) -> None:
        col = self.col_a_combo.currentText()
        popmean = self.popmean_spin.value()
        result = inferential.one_sample_ttest(self._df[col], popmean)
        self._render_ttest_result(result, f"H0: mean({col}) = {popmean:g}")

    def _run_two_sample_t(self) -> None:
        a_name = self.col_a_combo.currentText()
        b_name = self.col_b_combo.currentText()
        result = inferential.two_sample_ttest(self._df[a_name], self._df[b_name], equal_var=False)
        self._render_ttest_result(result, f"H0: mean({a_name}) = mean({b_name})  [Welch's t-test]")

    def _run_paired_t(self) -> None:
        a_name = self.col_a_combo.currentText()
        b_name = self.col_b_combo.currentText()
        result = inferential.paired_ttest(self._df[a_name], self._df[b_name])
        self._render_ttest_result(result, f"H0: mean difference ({a_name} - {b_name}) = 0")

    def _render_ttest_result(self, result, hypothesis: str) -> None:
        text = (
            f"{hypothesis}\n\n"
            f"t = {result.statistic:.4f}   df = {result.df:.2f}\n"
            f"Mean difference = {result.mean_diff:.4g}\n"
            f"95% CI of difference: [{result.ci_95_low:.4g}, {result.ci_95_high:.4g}]\n\n"
            f"{inferential.interpret_p_value(result.p_value)}"
        )
        self.result_text.setPlainText(text)
        self.chart.clear()
        self.chart.redraw()

    def _run_chi_square(self) -> None:
        a_name = self.col_a_combo.currentText()
        b_name = self.col_b_combo.currentText()
        result = inferential.chi_square_independence(self._df, a_name, b_name)

        caveat = "" if result.expected_valid else "\n\nWarning: some expected cell counts are below 5; the chi-square approximation may be unreliable."
        text = (
            f"H0: {a_name} and {b_name} are independent\n\n"
            f"chi2 = {result.statistic:.4f}   df = {result.df}\n\n"
            f"{inferential.interpret_p_value(result.p_value)}{caveat}"
        )
        self.result_text.setPlainText(text)

        import pandas as pd
        contingency = pd.crosstab(self._df[a_name].astype(str), self._df[b_name].astype(str))
        self.chart.clear()
        ax = self.chart.figure.add_subplot(111)
        im = ax.imshow(contingency.values, cmap="viridis", aspect="auto")
        ax.set_xticks(range(len(contingency.columns)))
        ax.set_xticklabels(contingency.columns, rotation=45, ha="right", fontsize=7)
        ax.set_yticks(range(len(contingency.index)))
        ax.set_yticklabels(contingency.index, fontsize=7)
        ax.set_title("Contingency table (counts)")
        self.chart.style_axes(ax)
        self.chart.redraw()

    def _run_anova(self) -> None:
        value_col = self.col_a_combo.currentText()
        group_col = self.group_combo.currentText()
        result = inferential.one_way_anova(self._df, value_col, group_col)

        text = (
            f"H0: all group means of {value_col} across {group_col} are equal\n\n"
            f"F = {result.statistic:.4f}   df_between = {result.df_between}   df_within = {result.df_within}\n"
            f"Groups: {', '.join(result.group_names)}\n\n"
            f"{inferential.interpret_p_value(result.p_value)}"
        )
        self.result_text.setPlainText(text)

        from core.data_loader import coerce_numeric
        self.chart.clear()
        ax = self.chart.figure.add_subplot(111)
        grouped = pd_group_values(self._df, value_col, group_col)
        if grouped:
            ax.boxplot(list(grouped.values()), labels=list(grouped.keys()))
        ax.set_title(f"{value_col} by {group_col}")
        ax.tick_params(axis="x", rotation=30)
        self.chart.style_axes(ax)
        self.chart.redraw()


def pd_group_values(df, value_col: str, group_col: str) -> dict:
    from core.data_loader import coerce_numeric
    out = {}
    values = coerce_numeric(df[value_col])
    groups = df[group_col].astype(str)
    for g in sorted(groups.dropna().unique()):
        vals = values[groups == g].dropna()
        if len(vals) > 0:
            out[g] = vals.to_numpy()
    return out
