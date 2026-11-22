"""Background task runner: QThread + worker object, results returned by signal."""

from __future__ import annotations

import traceback
from typing import Any, Callable

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from regression_studio.core.models import AnalysisError


class _Worker(QObject):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, func: Callable[..., Any], args: tuple) -> None:
        super().__init__()
        self._func = func
        self._args = args

    def run(self) -> None:
        try:
            self.succeeded.emit(self._func(*self._args))
        except AnalysisError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # unexpected: keep the UI alive, log the trace
            traceback.print_exc()
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class TaskRunner(QObject):
    """Runs one function at a time off the UI thread.

    Callbacks run on the UI thread. start() returns False if a task is
    already running.
    """

    busy_changed = pyqtSignal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: _Worker | None = None
        self._on_success: Callable[[Any], None] | None = None
        self._on_failure: Callable[[str], None] | None = None

    @property
    def busy(self) -> bool:
        return self._thread is not None

    def start(
        self,
        func: Callable[..., Any],
        *args: Any,
        on_success: Callable[[Any], None] | None = None,
        on_failure: Callable[[str], None] | None = None,
    ) -> bool:
        if self._thread is not None:
            return False
        self._on_success, self._on_failure = on_success, on_failure
        self._thread = QThread()
        self._worker = _Worker(func, args)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.succeeded.connect(self._handle_success)
        self._worker.failed.connect(self._handle_failure)
        self._worker.succeeded.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._cleanup)
        self.busy_changed.emit(True)
        self._thread.start()
        return True

    def _handle_success(self, result: object) -> None:
        if self._on_success is not None:
            self._on_success(result)

    def _handle_failure(self, message: str) -> None:
        if self._on_failure is not None:
            self._on_failure(message)

    def _cleanup(self) -> None:
        if self._thread is not None:
            self._thread.deleteLater()
        self._thread = None
        self._worker = None
        self.busy_changed.emit(False)

    def shutdown(self) -> None:
        """Block until a running task finishes (used when the window closes)."""
        if self._thread is not None:
            self._thread.wait(10000)
