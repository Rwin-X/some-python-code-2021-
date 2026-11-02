"""QThread worker objects. UI subscribes to these via signals only."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from core.data_loader import DataLoadError, classify_columns, load_table


class DataLoadWorker(QObject):
    """Loads and classifies a data file off the main thread."""

    finished = pyqtSignal(object, object)  # (DataFrame, kinds dict)
    failed = pyqtSignal(str)

    def __init__(self, path: str):
        super().__init__()
        self._path = path

    def run(self) -> None:
        try:
            df = load_table(self._path)
            kinds = classify_columns(df)
            self.finished.emit(df, kinds)
        except DataLoadError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # unexpected parse failures
            self.failed.emit(f"Unexpected error while loading file: {exc}")
