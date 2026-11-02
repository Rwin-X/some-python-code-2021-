"""Top-level application window: frameless chrome + tabbed content."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.models import ColumnKind
from ui.widgets.correlation_matrix_panel import CorrelationMatrixPanel
from ui.widgets.descriptive_panel import DescriptivePanel
from ui.widgets.inferential_panel import InferentialPanel
from ui.widgets.overview_panel import OverviewPanel
from ui.widgets.probability_panel import ProbabilityPanel
from ui.widgets.title_bar import TitleBar

APP_TITLE = "StatLab"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.resize(1180, 760)
        self.setMinimumSize(860, 560)

        central = QWidget()
        central.setObjectName("rootContainer")
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.title_bar = TitleBar(self, APP_TITLE)
        root_layout.addWidget(self.title_bar)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setContentsMargins(12, 12, 12, 12)

        self.overview_panel = OverviewPanel()
        self.descriptive_panel = DescriptivePanel()
        self.probability_panel = ProbabilityPanel()
        self.inferential_panel = InferentialPanel()
        self.correlation_panel = CorrelationMatrixPanel()

        self.tabs.addTab(self.overview_panel, "Data")
        self.tabs.addTab(self.descriptive_panel, "Descriptive")
        self.tabs.addTab(self.correlation_panel, "Correlation Matrix")
        self.tabs.addTab(self.inferential_panel, "Hypothesis Tests")
        self.tabs.addTab(self.probability_panel, "Probability")

        root_layout.addWidget(self.tabs, stretch=1)

        self.status_bar = QStatusBar()
        self.status_label = QLabel("No dataset loaded")
        self.status_bar.addWidget(self.status_label)
        root_layout.addWidget(self.status_bar)

        self.setCentralWidget(central)

        self.overview_panel.dataset_loaded.connect(self._on_dataset_loaded)
        self.overview_panel.load_failed.connect(self._on_load_failed)

    def _on_dataset_loaded(self, df, kinds: dict[str, ColumnKind], path: str) -> None:
        self.descriptive_panel.set_dataset(df, kinds)
        self.inferential_panel.set_dataset(df, kinds)
        self.correlation_panel.set_dataset(df, kinds)

        numeric_count = sum(1 for k in kinds.values() if k == ColumnKind.NUMERIC)
        categorical_count = sum(1 for k in kinds.values() if k == ColumnKind.CATEGORICAL)
        self.status_label.setText(
            f"{path}  |  {len(df):,} rows  |  {numeric_count} numeric, {categorical_count} categorical columns"
        )

    def _on_load_failed(self, message: str) -> None:
        self.status_label.setText(f"Load failed: {message}")
