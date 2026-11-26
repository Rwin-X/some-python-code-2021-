"""Left-side control panel: data input, series selection, chart options."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.models import ChartKind


class ControlPanel(QWidget):
    """Emits signals; never touches core/ directly."""

    sample_data_requested = pyqtSignal()
    csv_requested = pyqtSignal(str)
    series_added = pyqtSignal(str, str)  # name, raw_text
    series_removed = pyqtSignal(str)
    spec_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("sidePanel")
        self.setFixedWidth(300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(self._section_label("DATA SOURCE"))

        data_buttons = QHBoxLayout()
        self.sample_btn = QPushButton("Load sample")
        self.import_btn = QPushButton("Import CSV")
        data_buttons.addWidget(self.sample_btn)
        data_buttons.addWidget(self.import_btn)
        layout.addLayout(data_buttons)

        self.sample_btn.clicked.connect(self.sample_data_requested.emit)
        self.import_btn.clicked.connect(self._open_csv_dialog)

        layout.addWidget(self._section_label("ADD SERIES MANUALLY"))

        self.series_name_input = QLineEdit()
        self.series_name_input.setPlaceholderText("Series name")
        layout.addWidget(self.series_name_input)

        self.series_values_input = QPlainTextEdit()
        self.series_values_input.setPlaceholderText("Values, comma or line separated")
        self.series_values_input.setFixedHeight(64)
        layout.addWidget(self.series_values_input)

        self.add_series_btn = QPushButton("Add series")
        self.add_series_btn.setObjectName("primaryAction")
        self.add_series_btn.clicked.connect(self._emit_series_added)
        layout.addWidget(self.add_series_btn)

        layout.addWidget(self._section_label("SERIES"))

        self.series_list = QListWidget()
        self.series_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.series_list.setFixedHeight(110)
        self.series_list.itemSelectionChanged.connect(self.spec_changed.emit)
        layout.addWidget(self.series_list)

        self.remove_series_btn = QPushButton("Remove selected")
        self.remove_series_btn.setObjectName("destructiveAction")
        self.remove_series_btn.clicked.connect(self._emit_series_removed)
        layout.addWidget(self.remove_series_btn)

        layout.addWidget(self._section_label("CHART"))

        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItem("Line", ChartKind.LINE)
        self.chart_type_combo.addItem("Bar", ChartKind.BAR)
        self.chart_type_combo.addItem("Scatter", ChartKind.SCATTER)
        self.chart_type_combo.addItem("Histogram", ChartKind.HISTOGRAM)
        self.chart_type_combo.addItem("Box plot", ChartKind.BOX)
        self.chart_type_combo.currentIndexChanged.connect(self.spec_changed.emit)
        layout.addWidget(self.chart_type_combo)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Chart title")
        self.title_input.textChanged.connect(self.spec_changed.emit)
        layout.addWidget(self.title_input)

        axis_row = QHBoxLayout()
        self.x_label_input = QLineEdit()
        self.x_label_input.setPlaceholderText("X label")
        self.x_label_input.textChanged.connect(self.spec_changed.emit)
        self.y_label_input = QLineEdit()
        self.y_label_input.setPlaceholderText("Y label")
        self.y_label_input.textChanged.connect(self.spec_changed.emit)
        axis_row.addWidget(self.x_label_input)
        axis_row.addWidget(self.y_label_input)
        layout.addLayout(axis_row)

        bins_row = QHBoxLayout()
        bins_label = QLabel("Histogram bins")
        bins_label.setObjectName("secondaryLabel")
        self.bins_spin = QSpinBox()
        self.bins_spin.setRange(2, 100)
        self.bins_spin.setValue(10)
        self.bins_spin.valueChanged.connect(self.spec_changed.emit)
        bins_row.addWidget(bins_label)
        bins_row.addWidget(self.bins_spin)
        layout.addLayout(bins_row)

        options_row = QHBoxLayout()
        self.grid_checkbox = QCheckBox("Grid")
        self.grid_checkbox.setChecked(True)
        self.grid_checkbox.stateChanged.connect(self.spec_changed.emit)
        self.legend_checkbox = QCheckBox("Legend")
        self.legend_checkbox.setChecked(True)
        self.legend_checkbox.stateChanged.connect(self.spec_changed.emit)
        options_row.addWidget(self.grid_checkbox)
        options_row.addWidget(self.legend_checkbox)
        layout.addLayout(options_row)

        layout.addWidget(self._section_label("STATISTICS"))
        self.stats_label = QLabel("Select a series to see statistics")
        self.stats_label.setObjectName("monoLabel")
        self.stats_label.setWordWrap(True)
        layout.addWidget(self.stats_label)

        layout.addStretch()

        self.export_btn = QPushButton("Export chart as PNG")
        layout.addWidget(self.export_btn)

    def set_series_names(self, names: list[str]) -> None:
        previously_selected = self.selected_series_names()
        self.series_list.blockSignals(True)
        self.series_list.clear()
        for name in names:
            item = QListWidgetItem(name)
            self.series_list.addItem(item)
            if name in previously_selected or not previously_selected:
                item.setSelected(True)
        self.series_list.blockSignals(False)

    def selected_series_names(self) -> list[str]:
        return [item.text() for item in self.series_list.selectedItems()]

    def set_stats_text(self, text: str) -> None:
        self.stats_label.setText(text)

    def current_chart_kind(self) -> ChartKind:
        return self.chart_type_combo.currentData()

    def _section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionLabel")
        return label

    def _open_csv_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import CSV", "", "CSV files (*.csv)")
        if path:
            self.csv_requested.emit(path)

    def _emit_series_added(self) -> None:
        name = self.series_name_input.text().strip()
        raw_text = self.series_values_input.toPlainText().strip()
        if not name or not raw_text:
            return
        self.series_added.emit(name, raw_text)
        self.series_name_input.clear()
        self.series_values_input.clear()

    def _emit_series_removed(self) -> None:
        for name in self.selected_series_names():
            self.series_removed.emit(name)
