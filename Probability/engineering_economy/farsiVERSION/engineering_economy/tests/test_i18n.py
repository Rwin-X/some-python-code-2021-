import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import QThreadPool
from PyQt6.QtWidgets import QApplication

from ui.i18n import FA, header, plain, rich
from ui.main_window import MainWindow
from ui.style import build_stylesheet


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    a.setStyleSheet(build_stylesheet())
    return a


def test_helpers():
    assert plain("Loan") == "Loan (وام)"
    assert plain("unknown text") == "unknown text"
    assert header("Year") == "Year\n(سال)"
    assert "<span" in rich("Loan")


def test_every_visible_english_string_has_a_translation(app):
    w = MainWindow()
    QThreadPool.globalInstance().waitForDone()
    for _ in range(5):
        app.processEvents()
    missing = set()
    for p in w.pages:
        missing.add(p.title)
        for f in p.form._fields.values():
            missing.add(f.label)
            missing.update(str(c) for c in (f.choices or ()) if not str(c).isdigit())
        out = p.last_output
        for label, _value in out.items:
            missing.add(label)
        for title, cols, _rows in out.tables:
            missing.add(title)
            missing.update(cols)
    missing.discard("")
    assert not [m for m in missing if m not in FA], sorted(m for m in missing if m not in FA)
