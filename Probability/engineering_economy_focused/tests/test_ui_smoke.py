import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest
from PyQt6.QtCore import QThreadPool
from PyQt6.QtWidgets import QApplication

from core import dataset
from ui.i18n import FA, header, plain, rich
from ui.main_window import MainWindow
from ui.style import build_stylesheet

DATASET = Path(__file__).resolve().parents[1] / "data" / "hydraulic_jack_dataset.json"
SYMBOLS = {"(F/P,i,n)", "(P/F,i,n)", "(A/F,i,n)", "(A/P,i,n)", "(F/A,i,n)", "(P/A,i,n)"}


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    a.setStyleSheet(build_stylesheet())
    return a


def settle(app):
    QThreadPool.globalInstance().waitForDone()
    for _ in range(5):
        app.processEvents()


def pages(w):
    return {p.title: p for p in w.pages}


def test_all_pages_run_with_defaults(app):
    w = MainWindow()
    settle(app)
    for p in w.pages:
        assert p.status.text() == "", (p.title, p.status.text())
        assert p.last_output is not None, p.title


def test_dataset_matches_expected(app):
    w = MainWindow()
    w.apply_dataset(dataset.load(str(DATASET)))
    settle(app)
    by = pages(w)
    cmp_ = dict(by["ROR vs MARR"].last_output.items)
    assert cmp_["ROR"] == "22.008%" and cmp_["Difference (ROR - MARR)"] == "+7.008 pts"
    assert cmp_["Decision by ROR rule"] == "Accept" and cmp_["Rules agree"] == "Yes"
    assert dict(by["MARR"].last_output.items)["MARR"] == "15.000%"
    assert dict(by["Cash flow"].last_output.items)["Present worth"] == "121,423.18"
    assert dict(by["P-A-F-i"].last_output.items)["Annual amount A"] == "22,285.01"


def test_cash_flow_and_marr_are_shared_across_pages(app):
    w = MainWindow()
    settle(app)
    by = pages(w)
    by["Cash flow"].form.set_values({"cash_flows": [-100, 60, 60], "marr": 10})
    by["Cash flow"].run()
    settle(app)
    assert by["ROR"].form.values()["cash_flows"] == [-100.0, 60.0, 60.0]
    assert by["ROR vs MARR"].form.values()["marr"] == 10.0
    assert dict(by["ROR"].last_output.items)["ROR"] == "13.066%"


def test_marr_page_can_set_project_marr(app):
    w = MainWindow()
    settle(app)
    by = pages(w)
    by["MARR"].form.set_values({"premium_pct": 5})
    by["MARR"].run()
    settle(app)
    by["MARR"].apply_btn.click()
    settle(app)
    assert by["ROR vs MARR"].form.values()["marr"] == pytest.approx(18.2)


def test_bad_input_reports_error_without_crashing(app):
    w = MainWindow()
    settle(app)
    page = w.pages[0]
    page.form.set_values({"r": "abc"})
    page.run()
    assert "enter a number" in page.status.text()


def test_i18n_helpers_and_coverage(app):
    assert plain("ROR") == "ROR (نرخ بازگشت سرمایه)" and plain("unknown") == "unknown"
    assert header("Period") == "Period\n(دوره)" and "<span" in rich("ROR")
    w = MainWindow()
    settle(app)
    seen = set()
    for p in w.pages:
        seen.add(p.title)
        for f in p.form._fields.values():
            seen.add(f.label)
            seen.update(str(c) for c in (f.choices or ()))
        for label, _ in p.last_output.items:
            seen.add(label)
        for title, cols, rows in p.last_output.tables:
            seen.add(title)
            seen.update(cols)
            if "Description" in cols:
                seen.update(r[cols.index("Description")] for r in rows)
    seen.discard("")
    missing = sorted(s for s in seen if s not in FA and s not in SYMBOLS)
    assert not missing, missing
