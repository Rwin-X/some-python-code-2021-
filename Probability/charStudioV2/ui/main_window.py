"""ChartStudio main window: frameless chrome + chart workspace."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QMessageBox, QVBoxLayout, QWidget

from core.engine import DataEngine
from core.models import ChartSpec
from ui.widgets.chart_canvas import ChartCanvas
from ui.widgets.control_panel import ControlPanel
from ui.widgets.title_bar import TitleBar


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self.engine = DataEngine()
        self.spec = ChartSpec(title="Untitled chart", x_label="", y_label="")

        central = QWidget()
        central.setObjectName("rootContainer")
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.title_bar = TitleBar(self, "ChartStudio")
        root_layout.addWidget(self.title_bar)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.control_panel = ControlPanel()
        body_layout.addWidget(self.control_panel)

        self.canvas = ChartCanvas()
        body_layout.addWidget(self.canvas, stretch=1)

        root_layout.addWidget(body, stretch=1)

        self.setCentralWidget(central)
        self.resize(1180, 720)

        self._connect_signals()
        self.engine.load_sample_data()

    def _connect_signals(self) -> None:
        self.engine.dataset_changed.connect(self._on_dataset_changed)
        self.engine.import_failed.connect(self._on_import_failed)

        self.control_panel.sample_data_requested.connect(self.engine.load_sample_data)
        self.control_panel.csv_requested.connect(self.engine.load_csv)
        self.control_panel.series_added.connect(self.engine.set_manual_series)
        self.control_panel.series_removed.connect(self.engine.remove_series)
        self.control_panel.spec_changed.connect(self._on_spec_changed)
        self.control_panel.export_btn.clicked.connect(self._export_chart)

    def _on_dataset_changed(self) -> None:
        self.control_panel.set_series_names(self.engine.dataset.series_names())
        self._on_spec_changed()

    def _on_spec_changed(self) -> None:
        selected = self.control_panel.selected_series_names()
        self.spec.kind = self.control_panel.current_chart_kind()
        self.spec.title = self.control_panel.title_input.text()
        self.spec.x_label = self.control_panel.x_label_input.text()
        self.spec.y_label = self.control_panel.y_label_input.text()
        self.spec.bins = self.control_panel.bins_spin.value()
        self.spec.show_grid = self.control_panel.grid_checkbox.isChecked()
        self.spec.show_legend = self.control_panel.legend_checkbox.isChecked()
        self.spec.trend = self.control_panel.current_trend_kind()
        self.spec.moving_average_window = self.control_panel.moving_average_spin.value()
        self.spec.normalize = self.control_panel.normalize_checkbox.isChecked()
        self.spec.log_y = self.control_panel.log_y_checkbox.isChecked()
        self.spec.selected_series = selected

        self.canvas.render(self.engine.dataset, self.spec)
        self._update_stats_display(selected)

    def _update_stats_display(self, selected: list[str]) -> None:
        if not selected:
            self.control_panel.set_stats_text("Select a series to see statistics")
            return
        lines = []
        for name in selected:
            stats = self.engine.summary_stats(name)
            if stats is None:
                continue
            lines.append(
                f"{name}\n"
                f"  n={stats['count']:.0f}  mean={stats['mean']:.3f}\n"
                f"  median={stats['median']:.3f}  stdev={stats['stdev']:.3f}\n"
                f"  min={stats['min']:.3f}  max={stats['max']:.3f}"
            )
        self.control_panel.set_stats_text("\n\n".join(lines) if lines else "No numeric data")

    def _on_import_failed(self, message: str) -> None:
        QMessageBox.warning(self, "Import failed", message)

    def _export_chart(self) -> None:
        from PyQt6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(
            self, "Export chart", "chart.png", "PNG image (*.png)"
        )
        if path:
            self.canvas.figure.savefig(path, facecolor=self.canvas.figure.get_facecolor())
