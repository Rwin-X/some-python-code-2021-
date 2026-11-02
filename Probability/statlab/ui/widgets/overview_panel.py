"""Overview tab: load a file, preview rows, see detected column kinds."""

from __future__ import annotations

import os

import pandas as pd
from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.workers import DataLoadWorker

MAX_PREVIEW_ROWS = 200


class OverviewPanel(QWidget):
    """Lets the user pick a file, shows a preview, and reports loaded state."""

    dataset_loaded = pyqtSignal(object, object, str)  # (DataFrame, kinds, path)
    load_failed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._thread: QThread | None = None
        self._worker: DataLoadWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        self.load_btn = QPushButton("Open data file")
        self.load_btn.setObjectName("primaryAction")
        self.load_btn.clicked.connect(self._pick_file)
        header_row.addWidget(self.load_btn)

        self.file_label = QLabel("No file loaded")
        self.file_label.setObjectName("secondaryLabel")
        header_row.addWidget(self.file_label)
        header_row.addStretch()
        layout.addLayout(header_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate
        self.progress.setVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        self.status_label = QLabel("")
        self.status_label.setObjectName("tertiaryLabel")
        layout.addWidget(self.status_label)

        self.preview_table = QTableWidget()
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.setAlternatingRowColors(False)
        layout.addWidget(self.preview_table, stretch=1)

    def _pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open data file",
            "",
            "Data files (*.csv *.tsv *.txt *.xlsx *.xls);;All files (*)",
        )
        if path:
            self.load_file(path)

    def load_file(self, path: str) -> None:
        self.load_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.status_label.setText(f"Loading {os.path.basename(path)}...")

        self._thread = QThread()
        self._worker = DataLoadWorker(path)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(lambda df, kinds: self._on_loaded(df, kinds, path))
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_loaded(self, df, kinds, path: str) -> None:
        self.load_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.file_label.setText(os.path.basename(path))
        self.status_label.setText(
            f"{len(df):,} rows x {df.shape[1]} columns loaded from {path}"
        )
        self._populate_preview(df)
        self.dataset_loaded.emit(df, kinds, path)

    def _on_failed(self, message: str) -> None:
        self.load_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.status_label.setText(f"Load failed: {message}")
        self.load_failed.emit(message)

    def _populate_preview(self, df) -> None:
        preview = df.head(MAX_PREVIEW_ROWS)
        self.preview_table.clear()
        self.preview_table.setRowCount(len(preview))
        self.preview_table.setColumnCount(df.shape[1])
        self.preview_table.setHorizontalHeaderLabels([str(c) for c in df.columns])

        for row_idx in range(len(preview)):
            for col_idx, col_name in enumerate(df.columns):
                value = preview.iloc[row_idx, col_idx]
                try:
                    is_missing = bool(pd.isna(value))
                except (TypeError, ValueError):
                    is_missing = False
                text = "" if is_missing else str(value)
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.preview_table.setItem(row_idx, col_idx, item)

        self.preview_table.resizeColumnsToContents()
