"""Tests for core/models.py and core/engine.py.

Stubs PyQt6.QtCore so these run without PyQt6 installed -- engine.py
only needs QObject and pyqtSignal from it, and never uses Qt widgets.
"""

import math
import os
import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _install_pyqt_stub() -> None:
    if "PyQt6" in sys.modules:
        return

    qtcore = types.ModuleType("PyQt6.QtCore")

    class QObject:
        def __init__(self, *args, **kwargs):
            pass

    class _Signal:
        def __init__(self):
            self._subscribers = []

        def connect(self, fn):
            self._subscribers.append(fn)

        def emit(self, *args):
            for fn in self._subscribers:
                fn(*args)

    def pyqtSignal(*args, **kwargs):
        return property(lambda self: _Signal())

    qtcore.QObject = QObject
    qtcore.pyqtSignal = pyqtSignal

    pyqt6 = types.ModuleType("PyQt6")
    pyqt6.QtCore = qtcore
    sys.modules["PyQt6"] = pyqt6
    sys.modules["PyQt6.QtCore"] = qtcore


_install_pyqt_stub()

from core.engine import DataEngine
from core.models import ChartKind, ChartSpec, Dataset


def test_dataset_basics():
    dataset = Dataset()
    dataset.add_series("x", [1.0, 2.0, 3.0])
    assert dataset.series_names() == ["x"]
    assert dataset.row_count() == 3
    assert not dataset.is_empty()


def test_dataset_remove_and_rename():
    dataset = Dataset()
    dataset.add_series("x", [1.0])
    dataset.add_series("y", [2.0])
    dataset.remove_series("x")
    assert dataset.series_names() == ["y"]
    dataset.rename_series("y", "z")
    assert dataset.series_names() == ["z"]


def test_chart_spec_defaults():
    spec = ChartSpec()
    assert spec.kind == ChartKind.LINE
    assert spec.show_grid is True
    assert spec.normalize is False


def test_engine_manual_series_and_stats():
    engine = DataEngine.__new__(DataEngine)
    engine.dataset = Dataset()
    assert DataEngine.set_manual_series(engine, "A", "1, 2, 3, 4, 5")

    stats = DataEngine.summary_stats(engine, "A")
    assert stats["count"] == 5.0
    assert stats["mean"] == 3.0
    assert stats["median"] == 3.0
    assert stats["min"] == 1.0
    assert stats["max"] == 5.0


def test_engine_manual_series_rejects_empty():
    engine = DataEngine.__new__(DataEngine)
    engine.dataset = Dataset()
    assert not DataEngine.set_manual_series(engine, "A", "not,numbers,at,all")


def test_engine_csv_import_handles_bad_values():
    csv_text = "label,A,B\nrow1,1,10\nrow2,2,20\nrow3,bad,30\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as handle:
        handle.write(csv_text)
        path = handle.name

    try:
        engine = DataEngine.__new__(DataEngine)
        engine.dataset = Dataset()
        DataEngine.load_csv(engine, path)

        assert engine.dataset.series_names() == ["A", "B"]
        a_values = engine.dataset.get_series("A").values
        b_values = engine.dataset.get_series("B").values
        assert a_values[0] == 1.0
        assert a_values[1] == 2.0
        assert math.isnan(a_values[2])
        assert b_values == [10.0, 20.0, 30.0]
    finally:
        os.unlink(path)


def test_engine_summary_stats_missing_series_returns_none():
    engine = DataEngine.__new__(DataEngine)
    engine.dataset = Dataset()
    assert DataEngine.summary_stats(engine, "nonexistent") is None


if __name__ == "__main__":
    tests = [obj for name, obj in list(globals().items()) if name.startswith("test_")]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS  {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL  {test.__name__}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
