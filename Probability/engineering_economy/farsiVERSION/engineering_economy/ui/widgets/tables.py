"""Read-only result table factory."""
from PyQt6.QtCore import Qt
from ui.i18n import FA, header, plain
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem

LEFT_HEADERS = {"Symbol", "Description", "Applied", "Name", "Comparison", "Decision"}


def align_for(header: str) -> Qt.AlignmentFlag:
    side = Qt.AlignmentFlag.AlignLeft if header in LEFT_HEADERS else Qt.AlignmentFlag.AlignRight
    return side | Qt.AlignmentFlag.AlignVCenter


def make_table(columns, rows) -> QTableWidget:
    t = QTableWidget(len(rows), len(columns))
    t.setHorizontalHeaderLabels([header(c) for c in columns])
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(26)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    t.setShowGrid(False)
    t.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    for c, name in enumerate(columns):
        t.horizontalHeaderItem(c).setTextAlignment(align_for(name))
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            text = str(value)
            if columns[c] == "Description":  # long text: Persian goes in a tooltip
                item = QTableWidgetItem(text)
                item.setToolTip(FA.get(text, ""))
            else:
                item = QTableWidgetItem(plain(text))
                item.setToolTip(plain(text))  # full text when the cell is elided
            item.setTextAlignment(align_for(columns[c]))
            t.setItem(r, c, item)
    hdr = t.horizontalHeader()
    hdr.setStretchLastSection(False)
    hdr.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    # Let a text column absorb spare width; numeric tables stretch their last column.
    flex = 0 if columns[0] in LEFT_HEADERS else len(columns) - 1
    hdr.setSectionResizeMode(flex, QHeaderView.ResizeMode.Stretch)
    t.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    return t
