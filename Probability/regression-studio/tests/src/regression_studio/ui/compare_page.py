"""Compare tab: ranking of all single-predictor models."""

from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from regression_studio.core.models import ComparisonRow
from regression_studio.core.report import fmt

from .widgets import fill_table, make_readonly_table


class ComparePage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)
        self.note = QLabel("Press Compare to rank all single-predictor models on your data.")
        self.note.setObjectName("secondaryLabel")
        self.note.setWordWrap(True)
        lay.addWidget(self.note)
        self.table = make_readonly_table(
            ["Model", "R\u00b2", "Adjusted R\u00b2", "RMSE", "CV RMSE", "Note"]
        )
        lay.addWidget(self.table, 1)

    def show_rows(self, x_col: str, y_col: str, rows: list[ComparisonRow], n: int) -> None:
        fill_table(
            self.table,
            [
                [r.label, fmt(r.r2, 4), fmt(r.adj_r2, 4), fmt(r.rmse, 5), fmt(r.cv_rmse, 5), r.note]
                for r in rows
            ],
            accent_first=True,
        )
        self.note.setText(
            f"{y_col} vs {x_col}, {n} rows. Ranked by 5-fold cross-validated RMSE "
            "(lower is better); R\u00b2 and RMSE are in-sample and favour complex models."
        )
