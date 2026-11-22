import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest
from PyQt6.QtCore import QThreadPool
from PyQt6.QtWidgets import QApplication

from core import dataset
from ui.main_window import MainWindow
from ui.style import build_stylesheet

DATASET = Path(__file__).resolve().parents[1] / "data" / "hydraulic_jack_dataset.json"


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    a.setStyleSheet(build_stylesheet())
    return a


def settle(app):
    QThreadPool.globalInstance().waitForDone()
    for _ in range(5):
        app.processEvents()


def test_all_pages_run_with_defaults(app):
    w = MainWindow()
    settle(app)
    for p in w.pages:
        assert p.status.text() == "", (p.title, p.status.text())
        assert p.last_output is not None, p.title


def test_dataset_loading_matches_expected(app):
    w = MainWindow()
    w.apply_dataset(dataset.load(str(DATASET)))
    settle(app)
    by_title = {p.title: p for p in w.pages}
    alt = dict(by_title["Alternatives"].last_output.items)
    assert alt["Selected"].startswith("B")
    cf = dict(by_title["Cash flow"].last_output.items)
    assert cf["IRR"] == "22.011%" or cf["IRR"].startswith("22.0")
    assert dict(by_title["Capitalized cost"].last_output.items)["Capitalized cost"] == "435,518.99"


def test_bad_input_reports_error_without_crashing(app):
    w = MainWindow()
    settle(app)
    page = w.pages[0]
    page.form.set_values({"i": "abc"})
    page.run()
    assert "enter a number" in page.status.text()
