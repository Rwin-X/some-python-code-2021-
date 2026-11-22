"""Influence tab: outlier and leverage plot, flagged-point table, exclusion controls."""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QAbstractItemView, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from regression_studio.core.diagnostics import OUTLIER_LIMIT
from regression_studio.core.models import FitResult
from regression_studio.core.report import fmt

from .plots import InfluencePlot
from .widgets import fill_table, make_readonly_table

MAX_TABLE_ROWS = 50
FLAG_CODES = {"leverage": "L", "outlier": "O", "influential": "I"}


class InfluencePage(QWidget):
    exclude_requested = pyqtSignal(list)  # table row indices to exclude
    restore_requested = pyqtSignal()
    point_clicked = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(12)

        self.plot = InfluencePlot()
        self.plot.point_clicked.connect(self.point_clicked)
        lay.addWidget(self.plot, 1)

        side = QVBoxLayout()
        side.setSpacing(8)
        self.info = QLabel("Fit a model to see influence diagnostics.")
        self.info.setObjectName("secondaryLabel")
        self.info.setWordWrap(True)
        side.addWidget(self.info)

        self.table = make_readonly_table(
            ["Row", "Leverage", "Stud. res.", "Cook's D", "Flags"], compact=True
        )
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        side.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.btn_exclude = QPushButton("Exclude selected")
        self.btn_restore = QPushButton("Restore all")
        buttons.addWidget(self.btn_exclude)
        buttons.addWidget(self.btn_restore)
        side.addLayout(buttons)

        self.excluded_label = QLabel("")
        self.excluded_label.setObjectName("tertiaryLabel")
        self.excluded_label.setWordWrap(True)
        side.addWidget(self.excluded_label)
        lay.addLayout(side, 1)

        self.btn_exclude.clicked.connect(self._emit_exclude)
        self.btn_restore.clicked.connect(self.restore_requested)
        self.btn_exclude.setEnabled(False)
        self.btn_restore.setEnabled(False)

    def _emit_exclude(self) -> None:
        rows = {
            int(self.table.item(i.row(), 0).data(Qt.ItemDataRole.UserRole))
            for i in self.table.selectionModel().selectedRows()
        }
        if rows:
            self.exclude_requested.emit(sorted(rows))

    def show_result(self, r: FitResult) -> None:
        n, p = r.n, len(r.coef)
        self.plot.render(r)
        flagged = [i for i, f in enumerate(r.flags) if f]
        flagged.sort(key=lambda i: -(r.cooks[i] if np.isfinite(r.cooks[i]) else 0.0))
        shown = flagged[:MAX_TABLE_ROWS]
        fill_table(
            self.table,
            [
                [
                    str(int(r.row_index[i]) + 1),
                    fmt(float(r.leverage[i]), 4),
                    fmt(float(r.studentized[i]), 4),
                    fmt(float(r.cooks[i]), 4),
                    " ".join(FLAG_CODES[f] for f in r.flags[i]),
                ]
                for i in shown
            ],
        )
        for row, i in enumerate(shown):
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, int(r.row_index[i]))
        more = f" Showing the {MAX_TABLE_ROWS} largest." if len(flagged) > MAX_TABLE_ROWS else ""
        self.info.setText(
            f"{len(flagged)} of {n} points flagged (rules of thumb: leverage > 2p/n = {2 * p / n:.3g}, "
            f"|studentized residual| > {OUTLIER_LIMIT:g}, Cook's D > 4/n = {4 / n:.3g}).{more} "
            "Flags: L high leverage, O outlier, I influential. "
            "Click a point in the plot, or select rows and press Exclude, to refit without them."
        )
        excluded = np.sort(r.rows_excluded)
        if excluded.size:
            listed = ", ".join(str(int(i) + 1) for i in excluded[:30])
            suffix = " ..." if excluded.size > 30 else ""
            self.excluded_label.setText(f"Excluded rows ({excluded.size}): {listed}{suffix}")
        else:
            self.excluded_label.setText("No rows excluded.")
        self.btn_exclude.setEnabled(bool(shown))
        self.btn_restore.setEnabled(excluded.size > 0)
