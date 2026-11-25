"""Run a callable on the global QThreadPool and report back through signals."""
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal


class WorkerSignals(QObject):
    done = pyqtSignal(object)
    failed = pyqtSignal(str)


class Worker(QRunnable):
    def __init__(self, fn, *args):
        super().__init__()
        self.fn, self.args = fn, args
        self.signals = WorkerSignals()
        self.setAutoDelete(False)  # the owning page keeps the reference until done

    def run(self) -> None:
        try:
            out = self.fn(*self.args)
        except (ValueError, ZeroDivisionError, OverflowError) as exc:
            self.signals.failed.emit(str(exc) or "Invalid input")
            return
        except Exception as exc:  # noqa: BLE001 - surface anything unexpected in the UI
            self.signals.failed.emit(f"Unexpected error: {exc}")
            return
        self.signals.done.emit(out)
