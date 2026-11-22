"""Left control panel: data actions, model selection, prediction and export."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from regression_studio.core.engine import MAX_DEGREE
from regression_studio.core.models import AnalysisError, ModelKind, ModelSpec

from .widgets import ArrowComboBox, labeled, section_label


class Sidebar(QWidget):
    open_requested = pyqtSignal()
    save_requested = pyqtSignal()
    sample_requested = pyqtSignal()
    run_requested = pyqtSignal()
    compare_requested = pyqtSignal()
    predict_requested = pyqtSignal(str)
    export_plot_requested = pyqtSignal()
    export_report_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._syncing = False
        self.setObjectName("sidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(300)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)

        lay.addWidget(section_label("Data"))
        row = QHBoxLayout()
        row.setSpacing(8)
        self.btn_open = QPushButton("Open")
        self.btn_save = QPushButton("Save")
        self.btn_sample = QPushButton("Sample")
        for button in (self.btn_open, self.btn_save, self.btn_sample):
            row.addWidget(button)
        lay.addLayout(row)
        lay.addSpacing(8)

        lay.addWidget(section_label("Model"))
        self.model_combo = ArrowComboBox()
        for kind in ModelKind:
            self.model_combo.addItem(kind.label, kind)
        lay.addWidget(labeled("Regression type", self.model_combo))

        self.degree_combo = ArrowComboBox()
        self.degree_combo.addItems([str(d) for d in range(1, MAX_DEGREE + 1)])
        self.degree_combo.setCurrentIndex(1)  # degree 2
        self.degree_field = labeled("Polynomial degree", self.degree_combo)
        lay.addWidget(self.degree_field)

        self.y_combo = ArrowComboBox()
        lay.addWidget(labeled("Response (y)", self.y_combo))

        self.x_list = QListWidget()
        self.x_list.setFixedHeight(96)
        self.x_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        lay.addWidget(labeled("Predictors (x)", self.x_list))

        self.robust_check = QCheckBox("Robust standard errors (HC3)")
        self.robust_check.setToolTip(
            "Use heteroscedasticity-consistent standard errors for coefficient tests and intervals"
        )
        lay.addWidget(self.robust_check)

        run_row = QHBoxLayout()
        run_row.setSpacing(8)
        self.btn_run = QPushButton("Run")
        self.btn_run.setObjectName("primaryAction")
        self.btn_run.setToolTip("Fit the model (F5)")
        self.btn_compare = QPushButton("Compare")
        self.btn_compare.setToolTip("Fit all single-predictor models and rank them")
        run_row.addWidget(self.btn_run)
        run_row.addWidget(self.btn_compare)
        lay.addLayout(run_row)
        lay.addSpacing(8)

        lay.addWidget(section_label("Predict"))
        predict_row = QHBoxLayout()
        predict_row.setSpacing(8)
        self.predict_input = QLineEdit()
        self.predict_input.setPlaceholderText("Fit a model first")
        self.btn_predict = QPushButton("Go")
        self.btn_predict.setFixedWidth(56)
        predict_row.addWidget(self.predict_input, 1)
        predict_row.addWidget(self.btn_predict)
        lay.addLayout(predict_row)
        self.predict_output = QPlainTextEdit()
        self.predict_output.setObjectName("monoText")
        self.predict_output.setReadOnly(True)
        self.predict_output.setFixedHeight(96)
        lay.addWidget(self.predict_output)
        lay.addSpacing(8)

        lay.addWidget(section_label("Export"))
        export_row = QHBoxLayout()
        export_row.setSpacing(8)
        self.btn_export_plot = QPushButton("Plot")
        self.btn_export_report = QPushButton("Report")
        export_row.addWidget(self.btn_export_plot)
        export_row.addWidget(self.btn_export_report)
        lay.addLayout(export_row)
        lay.addStretch(1)

        self.set_result_actions_enabled(False)
        self._connect()
        self._update_model_controls()

    def _connect(self) -> None:
        self.btn_open.clicked.connect(self.open_requested)
        self.btn_save.clicked.connect(self.save_requested)
        self.btn_sample.clicked.connect(self.sample_requested)
        self.btn_run.clicked.connect(self.run_requested)
        self.btn_compare.clicked.connect(self.compare_requested)
        self.btn_predict.clicked.connect(self._emit_predict)
        self.predict_input.returnPressed.connect(self._emit_predict)
        self.btn_export_plot.clicked.connect(self.export_plot_requested)
        self.btn_export_report.clicked.connect(self.export_report_requested)
        self.model_combo.currentIndexChanged.connect(self._update_model_controls)
        self.y_combo.currentIndexChanged.connect(self._normalize_x_selection)
        self.x_list.itemChanged.connect(self._on_x_changed)

    def _emit_predict(self) -> None:
        self.predict_requested.emit(self.predict_input.text())

    # --- selection state ----------------------------------------------------

    def kind(self) -> ModelKind:
        return self.model_combo.currentData()

    def y_name(self) -> str:
        return self.y_combo.currentText()

    def checked_x(self) -> list[str]:
        return [
            self.x_list.item(i).text()
            for i in range(self.x_list.count())
            if self.x_list.item(i).checkState() == Qt.CheckState.Checked
        ]

    def read_spec(self, excluded: frozenset[int] = frozenset()) -> ModelSpec:
        predictors = tuple(self.checked_x())
        if not predictors:
            raise AnalysisError("Select a predictor column.")
        return ModelSpec(
            self.kind(),
            self.y_name(),
            predictors,
            int(self.degree_combo.currentText()),
            self.robust_check.isChecked(),
            excluded,
        )

    def set_columns(self, names: list[str]) -> None:
        previous_y = self.y_combo.currentText()
        previous_x = set(self.checked_x())
        self._syncing = True
        self.y_combo.clear()
        self.y_combo.addItems(names)
        index = self.y_combo.findText(previous_y)
        self.y_combo.setCurrentIndex(index if index >= 0 else len(names) - 1)
        self.x_list.clear()
        for name in names:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if name in previous_x else Qt.CheckState.Unchecked
            )
            self.x_list.addItem(item)
        self._syncing = False
        self._normalize_x_selection()

    def _normalize_x_selection(self, *_args) -> None:
        """Keep predictors valid: never the response; one only for single-x models."""
        if self._syncing:
            return
        self._syncing = True
        y_name = self.y_name()
        multiple = self.kind() is ModelKind.MULTIPLE
        seen_checked = False
        for i in range(self.x_list.count()):
            item = self.x_list.item(i)
            if item.text() == y_name:
                item.setCheckState(Qt.CheckState.Unchecked)
            elif item.checkState() == Qt.CheckState.Checked:
                if seen_checked and not multiple:
                    item.setCheckState(Qt.CheckState.Unchecked)
                seen_checked = True
        if not seen_checked:
            for i in range(self.x_list.count()):
                item = self.x_list.item(i)
                if item.text() != y_name:
                    item.setCheckState(Qt.CheckState.Checked)
                    break
        self._syncing = False

    def _on_x_changed(self, item: QListWidgetItem) -> None:
        if self._syncing:
            return
        self._syncing = True
        if self.kind() is not ModelKind.MULTIPLE and item.checkState() == Qt.CheckState.Checked:
            for i in range(self.x_list.count()):
                other = self.x_list.item(i)
                if other is not item:
                    other.setCheckState(Qt.CheckState.Unchecked)
        if item.text() == self.y_name():
            item.setCheckState(Qt.CheckState.Unchecked)
        self._syncing = False

    def _update_model_controls(self, *_args) -> None:
        self.degree_field.setVisible(self.kind() is ModelKind.POLYNOMIAL)
        self._normalize_x_selection()

    # --- state from the window ------------------------------------------------

    def set_busy(self, busy: bool) -> None:
        for button in (self.btn_run, self.btn_compare, self.btn_open, self.btn_save):
            button.setEnabled(not busy)

    def set_result_actions_enabled(self, enabled: bool) -> None:
        for button in (self.btn_predict, self.btn_export_plot, self.btn_export_report):
            button.setEnabled(enabled)

    def set_predict_hint(self, text: str) -> None:
        self.predict_input.setPlaceholderText(text)
        self.predict_output.clear()

    def show_prediction(self, text: str) -> None:
        self.predict_output.setPlainText(text)
