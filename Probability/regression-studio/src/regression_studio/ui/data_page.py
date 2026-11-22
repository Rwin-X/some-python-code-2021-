"""Data tab: editable table with row/column tools."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QInputDialog, QLabel, QPushButton, QVBoxLayout, QWidget

from .table import DataTableModel, DataTableView


class DataPage(QWidget):
    message = pyqtSignal(str)  # user-facing warnings for the window to show

    def __init__(self, model: DataTableModel) -> None:
        super().__init__()
        self.model = model
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        buttons = {
            "Add row": lambda: self.model.insert_rows(1),
            "Delete rows": self._delete_rows,
            "Add column": self.model.add_column,
            "Delete column": self._delete_column,
            "Clear": self.model.clear,
        }
        for text, handler in buttons.items():
            button = QPushButton(text)
            button.clicked.connect(handler)
            bar.addWidget(button)
        bar.addStretch(1)
        hint = QLabel("Double-click a header to rename. Ctrl+V pastes from a spreadsheet.")
        hint.setObjectName("tertiaryLabel")
        bar.addWidget(hint)
        lay.addLayout(bar)

        self.view = DataTableView()
        self.view.setModel(model)
        self.view.horizontalHeader().setDefaultSectionSize(110)
        self.view.verticalHeader().setDefaultSectionSize(26)
        self.view.horizontalHeader().sectionDoubleClicked.connect(self._rename_column)
        lay.addWidget(self.view, 1)

    def _delete_rows(self) -> None:
        rows = {i.row() for i in self.view.selectionModel().selectedIndexes()}
        current = self.view.currentIndex()
        if not rows and current.isValid():
            rows = {current.row()}
        self.model.remove_rows(sorted(rows))

    def _delete_column(self) -> None:
        index = self.view.currentIndex()
        if index.isValid():
            self.model.remove_column(index.column())

    def _rename_column(self, section: int) -> None:
        name, accepted = QInputDialog.getText(
            self, "Rename column", "Column name:", text=self.model.headers[section]
        )
        if accepted and not self.model.rename_column(section, name):
            self.message.emit("Column names must be non-empty and unique.")
