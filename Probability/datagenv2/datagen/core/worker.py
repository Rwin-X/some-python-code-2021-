"""Background worker. QObject/pyqtSignal only; no widgets."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from . import engine
from .models import GenerationConfig


class GenerateWorker(QObject):
    progress = pyqtSignal(int)         # 0-100
    finished = pyqtSignal(str, int)    # output path, record count
    failed = pyqtSignal(str)           # error message
    cancelled = pyqtSignal()

    def __init__(self, config: GenerationConfig):
        super().__init__()
        self._config = config
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            path = engine.write_output(
                self._config, self.progress.emit, lambda: self._cancel
            )
        except engine.Cancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.finished.emit(str(path), self._config.count)
