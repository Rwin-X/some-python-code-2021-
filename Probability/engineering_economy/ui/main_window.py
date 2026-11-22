"""Frameless main window: title bar, sidebar navigation, stacked pages."""
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QListWidget, QMainWindow,
                             QPushButton, QSizeGrip, QStackedWidget, QVBoxLayout, QWidget)

from core import dataset
from ui.pages import ALL_PAGES
from ui.widgets.titlebar import TitleBar

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("Engineering Economy")

        central = QWidget()
        central.setObjectName("rootContainer")
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(TitleBar(self, "Engineering Economy"))

        body = QHBoxLayout()
        body.setSpacing(0)
        side = QWidget()
        side.setObjectName("sidebar")
        side.setFixedWidth(196)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(10, 12, 10, 12)
        sv.setSpacing(8)

        self.pages = [cls() for cls in ALL_PAGES]
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.stack = QStackedWidget()
        for p in self.pages:
            self.nav.addItem(p.title)
            self.stack.addWidget(p)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)
        sv.addWidget(self.nav, 1)

        load_btn = QPushButton("Load dataset")
        load_btn.clicked.connect(self.choose_dataset)
        sv.addWidget(load_btn)
        self.load_status = QLabel("")
        self.load_status.setObjectName("status")
        self.load_status.setWordWrap(True)
        sv.addWidget(self.load_status)

        body.addWidget(side)
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)
        root.addWidget(QSizeGrip(self), 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)

        self.setCentralWidget(central)
        self.resize(1120, 740)
        self.setMinimumSize(980, 620)
        for p in self.pages:  # show results for the built-in sample data right away
            p.run()

    def _set_load_status(self, text: str, error: bool = False) -> None:
        self.load_status.setText(text)
        self.load_status.setProperty("error", error)
        self.load_status.style().unpolish(self.load_status)
        self.load_status.style().polish(self.load_status)

    def choose_dataset(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load dataset", str(DATA_DIR), "JSON (*.json)")
        if path:
            self.load_dataset_file(path)

    def load_dataset_file(self, path: str) -> None:
        try:
            data = dataset.load(path)
        except (OSError, ValueError) as exc:
            self._set_load_status(f"Could not load: {exc}", True)
            return
        self.apply_dataset(data)
        self._set_load_status(f"Loaded {Path(path).name}")

    def apply_dataset(self, data: dict) -> None:
        for p in self.pages:
            p.apply_dataset(data)
