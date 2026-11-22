"""Editable data grid: a string-backed table model and a spreadsheet-like view."""

from __future__ import annotations

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QApplication, QTableView

from regression_studio.core.io import clean_headers, looks_like_header, parse_delimited


class DataTableModel(QAbstractTableModel):
    """Holds the raw text of every cell; numeric parsing happens in core."""

    DEFAULT_ROWS = 25

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.headers: list[str] = ["x", "y"]
        self.rows: list[list[str]] = [["", ""] for _ in range(self.DEFAULT_ROWS)]

    # --- Qt model interface ---------------------------------------------
    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return self.rows[index.row()][index.column()]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False
        self.rows[index.row()][index.column()] = str(value).strip()
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
        return True

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return str(section + 1)

    def setHeaderData(self, section, orientation, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if orientation != Qt.Orientation.Horizontal:
            return False
        return self.rename_column(section, str(value))

    def flags(self, index):
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
        )

    # --- structure edits ----------------------------------------------------
    def rename_column(self, section: int, name: str) -> bool:
        name = name.strip()
        if not name or any(h == name for i, h in enumerate(self.headers) if i != section):
            return False
        self.headers[section] = name
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, section, section)
        return True

    def set_table(self, headers: list[str], rows: list[list[str]]) -> None:
        width = len(headers)
        self.beginResetModel()
        self.headers = list(headers)
        self.rows = [(list(r) + [""] * width)[:width] for r in rows]
        self.endResetModel()

    def insert_rows(self, count: int = 1) -> None:
        first = len(self.rows)
        self.beginInsertRows(QModelIndex(), first, first + count - 1)
        self.rows.extend([""] * len(self.headers) for _ in range(count))
        self.endInsertRows()

    def remove_rows(self, indices: list[int]) -> None:
        drop = set(indices)
        if not drop:
            return
        self.beginResetModel()
        self.rows = [r for i, r in enumerate(self.rows) if i not in drop]
        self.endResetModel()

    def add_column(self) -> None:
        n = len(self.headers) + 1
        name = f"col{n}"
        while name in self.headers:
            n += 1
            name = f"col{n}"
        self.beginInsertColumns(QModelIndex(), len(self.headers), len(self.headers))
        self.headers.append(name)
        for row in self.rows:
            row.append("")
        self.endInsertColumns()

    def remove_column(self, section: int) -> None:
        if len(self.headers) <= 1 or not 0 <= section < len(self.headers):
            return
        self.beginRemoveColumns(QModelIndex(), section, section)
        del self.headers[section]
        for row in self.rows:
            del row[section]
        self.endRemoveColumns()

    def clear(self) -> None:
        self.beginResetModel()
        self.rows = [[""] * len(self.headers) for _ in range(max(len(self.rows), 1))]
        self.endResetModel()

    def paste_block(self, row: int, col: int, block: list[list[str]]) -> None:
        """Paste cells at (row, col), growing the table when needed.

        When pasting at the top-left cell and the first pasted row is text,
        it becomes the column names instead of data.
        """
        if not block:
            return
        names: list[str] | None = None
        if row == 0 and col == 0 and looks_like_header(block[0]) and len(block) > 1:
            names, block = block[0], block[1:]
        width = max(len(r) for r in block)
        if names is not None:
            width = max(width, len(names))
        self.beginResetModel()
        while len(self.headers) < col + width:
            self.headers.append(f"col{len(self.headers) + 1}")
            for r in self.rows:
                r.append("")
        while len(self.rows) < row + len(block):
            self.rows.append([""] * len(self.headers))
        for i, line in enumerate(block):
            for j, cell in enumerate(line):
                self.rows[row + i][col + j] = cell
        if names is not None:
            merged = list(self.headers)
            merged[col : col + len(names)] = names
            self.headers = clean_headers(merged)
        self.endResetModel()


class DataTableView(QTableView):
    """QTableView with spreadsheet-style copy, paste and delete."""

    def keyPressEvent(self, event) -> None:
        model = self.model()
        if event.matches(QKeySequence.StandardKey.Paste):
            block = parse_delimited(QApplication.clipboard().text())
            index = self.currentIndex()
            row, col = (index.row(), index.column()) if index.isValid() else (0, 0)
            model.paste_block(row, col, block)
        elif event.matches(QKeySequence.StandardKey.Copy):
            QApplication.clipboard().setText(self._selection_as_text())
        elif event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            for index in self.selectionModel().selectedIndexes():
                model.setData(index, "")
        else:
            super().keyPressEvent(event)

    def _selection_as_text(self) -> str:
        indexes = self.selectionModel().selectedIndexes()
        if not indexes:
            return ""
        rows = sorted({i.row() for i in indexes})
        cols = sorted({i.column() for i in indexes})
        cells = {(i.row(), i.column()): i.data() for i in indexes}
        return "\n".join(
            "\t".join(str(cells.get((r, c), "")) for c in cols) for r in rows
        )
