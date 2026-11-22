"""Results tab: equation, coefficient table and model notes."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from regression_studio.core.models import FitResult
from regression_studio.core.report import coefficient_headers, coefficient_rows

from .widgets import fill_table, make_readonly_table


class ResultsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)
        self.equation = QLabel("No model fitted yet.")
        self.equation.setObjectName("equationLabel")
        self.equation.setWordWrap(True)
        self.equation.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.equation)
        self.table = make_readonly_table(
            ["Term", "Estimate", "Std. error", "t", "p-value", "CI low", "CI high"]
        )
        lay.addWidget(self.table, 1)
        self.notes = QLabel("")
        self.notes.setObjectName("tertiaryLabel")
        self.notes.setWordWrap(True)
        lay.addWidget(self.notes)

    def show_result(self, result: FitResult) -> None:
        self.equation.setText(result.equation)
        self.table.setHorizontalHeaderLabels(coefficient_headers(result))
        fill_table(self.table, coefficient_rows(result))
        self.notes.setText("  ".join(result.notes))
