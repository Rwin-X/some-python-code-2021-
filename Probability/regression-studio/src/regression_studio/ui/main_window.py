"""Main window: wires the sidebar, dashboard cards and tabbed pages together."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QSizeGrip,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from regression_studio import APP_NAME
from regression_studio.core.data import parse_points, sample_table
from regression_studio.core.engine import analyze, analyze_compare, predict
from regression_studio.core.io import read_table, write_csv
from regression_studio.core.models import AnalysisError, ComparisonRow, FitResult
from regression_studio.core.report import build_report, fmt, fmt_p, format_prediction

from .compare_page import ComparePage
from .data_page import DataPage
from .influence_page import InfluencePage
from .plots import DiagnosticsPlot, FitPlot, ResidualPlot, _PlotBase
from .results_page import ResultsPage
from .sidebar import Sidebar
from .table import DataTableModel
from .title_bar import TitleBar
from .widgets import MetricCard
from .workers import TaskRunner

CARDS = (
    ("r2", "R\u00b2"),
    ("adj_r2", "Adjusted R\u00b2"),
    ("rmse", "RMSE"),
    ("mae", "MAE"),
    ("f_p", "F-test p-value"),
    ("n", "Observations"),
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle(APP_NAME)
        self._result: FitResult | None = None
        self._excluded: set[int] = set()  # table rows the user left out of the fit

        self.table_model = DataTableModel(self)
        self._fit_runner = TaskRunner(self)
        self._io_runner = TaskRunner(self)

        self._build_ui()
        self._connect_signals()
        self.sidebar.set_columns(self.table_model.headers)
        self.resize(1280, 800)
        self.setMinimumSize(1000, 680)

    # --- construction -------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("rootContainer")
        central.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        root = QVBoxLayout(central)
        root.setContentsMargins(1, 1, 1, 1)
        root.setSpacing(0)

        self.title_bar = TitleBar(self, APP_NAME)
        root.addWidget(self.title_bar)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        self.sidebar = Sidebar()
        body_layout.addWidget(self.sidebar)
        body_layout.addWidget(self._build_workspace(), 1)
        root.addWidget(body, 1)

        footer = QWidget()
        footer.setObjectName("footerBar")
        footer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 4, 4, 4)
        self.status_label = QLabel("Enter data, paste from a spreadsheet, or open a CSV file.")
        self.status_label.setObjectName("tertiaryLabel")
        self.size_grip = QSizeGrip(self)
        footer_layout.addWidget(self.status_label, 1)
        footer_layout.addWidget(
            self.size_grip, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight
        )
        root.addWidget(footer)
        self.setCentralWidget(central)

    def _build_workspace(self) -> QWidget:
        work = QWidget()
        lay = QVBoxLayout(work)
        lay.setContentsMargins(16, 16, 16, 12)
        lay.setSpacing(12)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.cards: dict[str, MetricCard] = {}
        for key, title in CARDS:
            self.cards[key] = MetricCard(title)
            cards.addWidget(self.cards[key])
        lay.addLayout(cards)

        self.data_page = DataPage(self.table_model)
        self.fit_plot = FitPlot()
        self.resid_plot = ResidualPlot()
        self.diag_plot = DiagnosticsPlot()
        self.influence_page = InfluencePage()
        self.results_page = ResultsPage()
        self.compare_page = ComparePage()
        self.report_view = QPlainTextEdit()
        self.report_view.setObjectName("monoText")
        self.report_view.setReadOnly(True)
        self.report_view.setPlaceholderText("The full text report appears here after a fit.")

        self.tabs = QTabWidget()
        for widget, title in (
            (self.data_page, "Data"),
            (self.fit_plot, "Fit"),
            (self.resid_plot, "Residuals"),
            (self.diag_plot, "Diagnostics"),
            (self.influence_page, "Influence"),
            (self.results_page, "Results"),
            (self.compare_page, "Compare"),
            (self.report_view, "Report"),
        ):
            self.tabs.addTab(widget, title)
        lay.addWidget(self.tabs, 1)
        return work

    def _connect_signals(self) -> None:
        sb = self.sidebar
        sb.open_requested.connect(self._open_csv)
        sb.save_requested.connect(self._save_csv)
        sb.sample_requested.connect(self._load_sample)
        sb.run_requested.connect(self._run_fit)
        sb.compare_requested.connect(self._run_compare)
        sb.predict_requested.connect(self._predict)
        sb.export_plot_requested.connect(self._export_plot)
        sb.export_report_requested.connect(self._export_report)

        self.data_page.message.connect(self._notify)
        for signal in (
            self.table_model.headerDataChanged,
            self.table_model.modelReset,
            self.table_model.columnsInserted,
            self.table_model.columnsRemoved,
        ):
            signal.connect(self._on_columns_changed)
        # Row identity changes invalidate exclusions (they are table row indices).
        self.table_model.modelReset.connect(self._clear_exclusions)
        self.table_model.rowsRemoved.connect(self._clear_exclusions)

        for plot in (self.fit_plot, self.resid_plot, self.influence_page):
            plot.point_clicked.connect(self._toggle_exclusion)
        self.influence_page.exclude_requested.connect(self._exclude_rows)
        self.influence_page.restore_requested.connect(self._restore_all)

        for runner in (self._fit_runner, self._io_runner):
            runner.busy_changed.connect(sb.set_busy)
        for sequence in ("F5", "Ctrl+Return"):
            QShortcut(QKeySequence(sequence), self).activated.connect(self._run_fit)

    def _clear_exclusions(self, *_args) -> None:
        # A method, not set.clear: self._excluded is rebound after every fit.
        self._excluded = set()

    def _on_columns_changed(self, *_args) -> None:
        self.sidebar.set_columns(self.table_model.headers)

    # --- files --------------------------------------------------------------------

    def _open_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open data", "", "Data files (*.csv *.tsv *.txt);;All files (*)"
        )
        if not path:
            return
        self._set_status(f"Loading {Path(path).name}...")
        self._io_runner.start(
            read_table, path,
            on_success=lambda table, p=path: self._on_loaded(p, table),
            on_failure=self._on_task_failed,
        )

    def _on_loaded(self, path: str, table: tuple[list[str], list[list[str]]]) -> None:
        headers, rows = table
        self.table_model.set_table(headers, rows)
        self.tabs.setCurrentWidget(self.data_page)
        self._set_status(f"Loaded {len(rows)} rows, {len(headers)} columns from {Path(path).name}.")

    def _save_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save data", "data.csv", "CSV (*.csv)")
        if not path:
            return
        headers, rows = self._snapshot()
        self._io_runner.start(
            write_csv, path, headers, rows,
            on_success=lambda count, p=path: self._set_status(f"Saved {count} rows to {Path(p).name}."),
            on_failure=self._on_task_failed,
        )

    def _load_sample(self) -> None:
        headers, rows = sample_table()
        self.table_model.set_table(headers, rows)
        self.tabs.setCurrentWidget(self.data_page)
        self._set_status("Sample data loaded: y depends on x (quadratic) and z (linear).")

    # --- analysis -------------------------------------------------------------------

    def _snapshot(self) -> tuple[list[str], list[list[str]]]:
        return list(self.table_model.headers), [list(r) for r in self.table_model.rows]

    def _run_fit(self) -> None:
        if self._fit_runner.busy:
            return
        try:
            spec = self.sidebar.read_spec(frozenset(self._excluded))
        except AnalysisError as exc:
            self._notify(str(exc))
            return
        self._start_fit(spec, switch_tab=True, on_failure=self._on_task_failed)

    def _start_fit(self, spec, switch_tab: bool, on_failure: Callable[[str], None]) -> None:
        headers, rows = self._snapshot()
        self._set_status("Fitting...")
        self._fit_runner.start(
            analyze, headers, rows, spec,
            on_success=lambda result, s=switch_tab: self._on_fit_done(result, s),
            on_failure=on_failure,
        )

    def _run_compare(self) -> None:
        if self._fit_runner.busy:
            return
        predictors = self.sidebar.checked_x()
        if len(predictors) != 1:
            self._notify("Comparison needs exactly one predictor column.")
            return
        x_col, y_col = predictors[0], self.sidebar.y_name()
        headers, rows = self._snapshot()
        self._set_status("Comparing models...")
        self._fit_runner.start(
            analyze_compare, headers, rows, x_col, y_col, frozenset(self._excluded),
            on_success=lambda res: self._on_compare_done(x_col, y_col, res),
            on_failure=self._on_task_failed,
        )

    def _on_fit_done(self, result: FitResult, switch_tab: bool) -> None:
        self._result = result
        self._excluded = {int(i) for i in result.rows_excluded}
        self.cards["r2"].set_value(fmt(result.r2, 4))
        self.cards["adj_r2"].set_value(fmt(result.adj_r2, 4))
        self.cards["rmse"].set_value(fmt(result.rmse, 5))
        self.cards["mae"].set_value(fmt(result.mae, 5))
        self.cards["f_p"].set_value(fmt_p(result.f_p))
        self.cards["n"].set_value(str(result.n))

        self.fit_plot.render(result)
        self.resid_plot.render(result)
        self.diag_plot.render(result)
        self.influence_page.show_result(result)
        self.results_page.show_result(result)
        self.report_view.setPlainText(build_report(result))

        names = ", ".join(result.spec.x_cols)
        self.sidebar.set_predict_hint(
            "e.g. 2.5, 4, 7" if len(result.spec.x_cols) == 1 else f"{names}  (; between points)"
        )
        self.sidebar.set_result_actions_enabled(True)
        if switch_tab:
            self.tabs.setCurrentWidget(self.fit_plot)

        skipped = f", {result.n_dropped} incomplete rows skipped" if result.n_dropped else ""
        left_out = f", {result.rows_excluded.size} excluded" if result.rows_excluded.size else ""
        self._set_status(
            f"{result.spec.describe()} fitted on {result.n} rows{skipped}{left_out}. "
            "Click a point to exclude or restore it."
        )

    def _on_compare_done(self, x_col: str, y_col: str, payload: tuple[list[ComparisonRow], int]) -> None:
        rows, n = payload
        self.compare_page.show_rows(x_col, y_col, rows, n)
        self.tabs.setCurrentWidget(self.compare_page)
        self._set_status("Model comparison finished.")

    def _on_task_failed(self, message: str) -> None:
        self._set_status("Failed.")
        self._notify(message)

    # --- exclusions -------------------------------------------------------------

    def _refit_with_excluded(self, new_excluded: set[int]) -> None:
        """Refit the current model with a different excluded set; undo on failure."""
        if self._result is None or self._fit_runner.busy:
            return
        previous = set(self._excluded)
        self._excluded = new_excluded
        spec = dataclasses.replace(self._result.spec, excluded=frozenset(new_excluded))

        def revert(message: str) -> None:
            self._excluded = previous
            self._on_task_failed(message)

        self._start_fit(spec, switch_tab=False, on_failure=revert)

    def _toggle_exclusion(self, row: int) -> None:
        self._refit_with_excluded(set(self._excluded) ^ {row})

    def _exclude_rows(self, rows: list[int]) -> None:
        self._refit_with_excluded(set(self._excluded) | set(rows))

    def _restore_all(self) -> None:
        self._refit_with_excluded(set())

    # --- prediction & export ------------------------------------------------------

    def _predict(self, text: str) -> None:
        if self._result is None:
            return
        try:
            points = parse_points(text, self._result.x.shape[1])
            pred = predict(self._result, points)
        except AnalysisError as exc:
            self.sidebar.show_prediction(f"Error: {exc}")
            return
        self.sidebar.show_prediction(format_prediction(self._result, pred))

    def _export_plot(self) -> None:
        current = self.tabs.currentWidget()
        if isinstance(current, InfluencePage):
            canvas = current.plot
        elif isinstance(current, _PlotBase):
            canvas = current
        else:
            canvas = self.fit_plot
        path, _ = QFileDialog.getSaveFileName(
            self, "Export plot", "plot.png", "PNG (*.png);;SVG (*.svg);;PDF (*.pdf)"
        )
        if path:
            if not Path(path).suffix:
                path += ".png"
            canvas.figure.savefig(path, dpi=200, facecolor=canvas.figure.get_facecolor())
            self._set_status(f"Plot saved to {Path(path).name}.")

    def _export_report(self) -> None:
        if self._result is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export report", "regression_report.txt", "Text (*.txt)"
        )
        if path:
            Path(path).write_text(build_report(self._result), encoding="utf-8")
            self._set_status(f"Report saved to {Path(path).name}.")

    # --- helpers --------------------------------------------------------------------

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def _notify(self, message: str) -> None:
        QMessageBox.warning(self, APP_NAME, message)

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.WindowStateChange:
            self.title_bar.sync_maximize_glyph()
            self.size_grip.setVisible(not self.isMaximized())
        super().changeEvent(event)

    def closeEvent(self, event) -> None:
        self._fit_runner.shutdown()
        self._io_runner.shutdown()
        super().closeEvent(event)
