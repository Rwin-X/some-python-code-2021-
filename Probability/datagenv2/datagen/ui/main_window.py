"""Main window: field list, options, output path, generate/cancel."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, QTimer
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..core import engine
from ..core.formats import FORMAT_BY_KEY, FORMATS, KNOWN_EXTENSIONS
from ..core.models import GenerationConfig
from ..core.worker import GenerateWorker
from .widgets import FieldRow, TitleBar, TypeCombo

APP_TITLE = "Data Generator"

DEFAULT_FIELDS = (
    ("id", "sequence", ""),
    ("name", "full_name", ""),
    ("email", "email", ""),
    ("age", "integer", "18, 90"),
    ("created_at", "date", "2020-01-01, 2025-12-31"),
)


def _repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def _caption(text: str, object_name: str = "secondaryLabel") -> QLabel:
    label = QLabel(text)
    label.setObjectName(object_name)
    return label


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle(APP_TITLE)

        self._rows: list[FieldRow] = []
        self._thread: QThread | None = None
        self._worker: GenerateWorker | None = None
        self._busy = False

        central = QWidget()
        central.setObjectName("rootContainer")
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.title_bar = TitleBar(self, APP_TITLE)
        root.addWidget(self.title_bar)
        root.addWidget(self._build_content(), 1)

        self.setCentralWidget(central)
        self.resize(820, 600)
        self.setMinimumSize(660, 480)

        for name, type_key, params in DEFAULT_FIELDS:
            self._add_row(name, type_key, params)

    # --- layout ------------------------------------------------------------

    def _build_content(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 14)
        layout.setSpacing(14)

        # Everything that must be locked while a run is in progress.
        self.form = QWidget()
        form = QVBoxLayout(self.form)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(_caption("Fields"))
        header.addStretch()
        self.add_btn = QPushButton("Add field")
        self.add_btn.clicked.connect(lambda: self._add_row())
        header.addWidget(self.add_btn)
        form.addLayout(header)

        form.addLayout(self._build_column_labels())
        form.addWidget(self._build_field_list(), 1)
        form.addLayout(self._build_options_row())
        form.addLayout(self._build_output_row())
        layout.addWidget(self.form, 1)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        footer = QHBoxLayout()
        footer.setSpacing(12)
        self.status = QLabel("")
        self.status.setObjectName("statusLabel")
        self.status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        footer.addWidget(self.status, 1)

        self.generate_btn = QPushButton("Generate")
        self.generate_btn.setObjectName("primaryAction")
        self.generate_btn.setFixedWidth(120)
        self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        footer.addWidget(self.generate_btn)

        grip = QSizeGrip(self)
        grip.setFixedSize(16, 16)
        footer.addWidget(grip, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        layout.addLayout(footer)
        return content

    def _build_column_labels(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 6, 0)
        row.setSpacing(FieldRow.SPACING)
        for text, stretch in zip(("Name", "Type", "Parameters"), FieldRow.COLUMN_STRETCH):
            row.addWidget(_caption(text, "tertiaryLabel"), stretch)
        spacer = QWidget()
        spacer.setFixedWidth(FieldRow.REMOVE_SIZE)
        row.addWidget(spacer)
        return row

    def _build_field_list(self) -> QScrollArea:
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        holder = QWidget()
        self.rows_layout = QVBoxLayout(holder)
        self.rows_layout.setContentsMargins(0, 0, 6, 0)
        self.rows_layout.setSpacing(8)
        self.rows_layout.addStretch()
        self.scroll.setWidget(holder)
        return self.scroll

    def _build_options_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)

        row.addWidget(_caption("Records"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, engine.MAX_RECORDS)
        self.count_spin.setValue(100)
        self.count_spin.setGroupSeparatorShown(True)
        self.count_spin.setFixedWidth(120)
        row.addWidget(self.count_spin)

        row.addSpacing(16)
        row.addWidget(_caption("Seed"))
        self.seed_edit = QLineEdit()
        self.seed_edit.setPlaceholderText("empty = different every run")
        self.seed_edit.setFixedWidth(240)
        self.seed_edit.setToolTip("Use the same seed to get identical data again")
        row.addWidget(self.seed_edit)
        row.addStretch()
        return row

    def _build_output_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(_caption("Output"))
        self.path_edit = QLineEdit(str(Path.home() / "data.json"))
        row.addWidget(self.path_edit, 1)

        self.format_combo = TypeCombo()
        for spec in FORMATS:
            self.format_combo.addItem(spec.label, spec.key)
        self.format_combo.setFixedWidth(140)
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        row.addWidget(self.format_combo)

        browse = QPushButton("Browse")
        browse.clicked.connect(self._on_browse)
        row.addWidget(browse)
        return row

    # --- field rows --------------------------------------------------------

    def _add_row(self, name: str = "", type_key: str = "word", params: str = "") -> None:
        if not name:
            number = len(self._rows) + 1
            existing = {row.name_edit.text() for row in self._rows}
            while f"field_{number}" in existing:
                number += 1
            name = f"field_{number}"

        row = FieldRow(name, type_key, params)
        row.remove_requested.connect(self._remove_row)
        self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)
        self._rows.append(row)

        # A bound method is dropped safely if the window is destroyed first.
        QTimer.singleShot(0, self._scroll_to_end)

    def _scroll_to_end(self) -> None:
        bar = self.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _remove_row(self, row: FieldRow) -> None:
        if row in self._rows:
            self._rows.remove(row)
        self.rows_layout.removeWidget(row)
        row.setParent(None)
        row.deleteLater()

    # --- actions -----------------------------------------------------------

    def _format_spec(self):
        return FORMAT_BY_KEY[self.format_combo.currentData()]

    def _on_format_changed(self) -> None:
        """Swap a known extension in the path so it matches the new format."""
        path = Path(self.path_edit.text().strip())
        if path.name and path.suffix in KNOWN_EXTENSIONS:
            self.path_edit.setText(str(path.with_suffix(self._format_spec().extension)))

    def _on_browse(self) -> None:
        spec = self._format_spec()
        path, _ = QFileDialog.getSaveFileName(
            self, "Save file", self.path_edit.text(), f"{spec.label} files (*{spec.extension})"
        )
        if path:
            self.path_edit.setText(path)

    def _collect_config(self) -> GenerationConfig:
        return GenerationConfig(
            fields=tuple(row.to_spec() for row in self._rows),
            count=self.count_spin.value(),
            path=self.path_edit.text(),
            seed=self.seed_edit.text().strip() or None,
            format_key=self.format_combo.currentData(),
        )

    def _on_generate_clicked(self) -> None:
        if self._busy:
            if self._worker is not None:
                self._worker.cancel()
            self._set_status("Cancelling...")
            return
        self._start()

    def _start(self) -> None:
        config = self._collect_config()
        try:
            path = engine.validate(config)
        except ValueError as exc:
            self._set_status(str(exc), "error")
            return

        self.path_edit.setText(str(path))
        config = replace(config, path=str(path))

        self.progress.setValue(0)
        self._set_busy(True)
        self._set_status("Generating...")

        self._thread = QThread()
        self._worker = GenerateWorker(config)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.progress.setValue)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.cancelled.connect(self._on_cancelled)

        for signal in (self._worker.finished, self._worker.failed, self._worker.cancelled):
            signal.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_finished(self, path: str, count: int) -> None:
        self.progress.setValue(100)
        self._set_busy(False)
        self._set_status(f"Wrote {count:,} records to {Path(path).name}", "ok", tooltip=path)

    def _on_failed(self, message: str) -> None:
        self.progress.setValue(0)
        self._set_busy(False)
        self._set_status(message, "error")

    def _on_cancelled(self) -> None:
        self.progress.setValue(0)
        self._set_busy(False)
        self._set_status("Cancelled")

    # --- state helpers -----------------------------------------------------

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.form.setEnabled(not busy)
        self.generate_btn.setText("Cancel" if busy else "Generate")
        self.generate_btn.setObjectName("destructiveAction" if busy else "primaryAction")
        _repolish(self.generate_btn)

    def _set_status(self, text: str, state: str = "", tooltip: str = "") -> None:
        self.status.setText(text)
        self.status.setToolTip(tooltip or text)
        self.status.setProperty("state", state)
        _repolish(self.status)

    def closeEvent(self, event) -> None:
        if self._busy and self._worker is not None and self._thread is not None:
            self._worker.cancel()
            self._thread.quit()
            self._thread.wait(5000)
        super().closeEvent(event)
