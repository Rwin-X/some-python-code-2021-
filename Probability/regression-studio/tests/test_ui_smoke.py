import time

import numpy as np
import pytest

pytest.importorskip("PyQt6")
pytest.importorskip("matplotlib")

from matplotlib.backend_bases import MouseEvent  # noqa: E402
from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox  # noqa: E402

from regression_studio.core.models import ModelKind  # noqa: E402
from regression_studio.ui.main_window import MainWindow  # noqa: E402
from regression_studio.ui.style import build_stylesheet  # noqa: E402


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    instance.setStyleSheet(build_stylesheet())
    return instance


@pytest.fixture
def window(app, monkeypatch):
    warnings: list[str] = []
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text: warnings.append(text))
    win = MainWindow()
    win.warnings = warnings
    win.show()
    yield win
    win.close()


def wait_until(app, predicate, timeout=15.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return False


def settle(app, win):
    assert wait_until(app, lambda: not win._fit_runner.busy)


def run_fit(app, win):
    win._run_fit()
    assert wait_until(app, lambda: win._result is not None)
    settle(app, win)


def select_kind(win, kind):
    box = win.sidebar.model_combo
    box.setCurrentIndex(box.findData(kind))


def test_fit_on_sample_data(app, window):
    window._load_sample()
    select_kind(window, ModelKind.POLYNOMIAL)
    run_fit(app, window)
    assert window._result.spec.degree == 2
    assert window.cards["n"]._value.text() == "40"
    assert window.results_page.table.rowCount() == 3
    assert "y = " in window.results_page.equation.text()
    assert window.sidebar.btn_predict.isEnabled()
    window._predict("5")
    assert "y = " in window.sidebar.predict_output.toPlainText()
    assert not window.grab().isNull()
    assert not window.warnings


def test_multiple_regression_and_selection_rules(app, window):
    sb = window.sidebar
    window._load_sample()
    select_kind(window, ModelKind.LINEAR)
    # Single-predictor models keep exactly one predictor: checking z replaces x.
    sb.x_list.item(1).setCheckState(Qt.CheckState.Checked)
    assert sb.checked_x() == ["z"]
    select_kind(window, ModelKind.MULTIPLE)
    sb.x_list.item(0).setCheckState(Qt.CheckState.Checked)
    assert sb.checked_x() == ["x", "z"]
    # The response column can never be a predictor.
    sb.x_list.item(2).setCheckState(Qt.CheckState.Checked)
    assert "y" not in sb.checked_x()
    run_fit(app, window)
    assert window._result.x.shape[1] == 2


def test_errors_are_reported_not_raised(app, window):
    window.table_model.set_table(["x", "y"], [["1", "a"], ["2", "b"], ["3", "c"]])
    window._run_fit()
    assert wait_until(app, lambda: bool(window.warnings))
    settle(app, window)
    assert "not numeric" in window.warnings[0]
    assert window._result is None


def test_compare_fills_table(app, window):
    window._load_sample()
    window._run_compare()
    assert wait_until(app, lambda: window.compare_page.table.rowCount() > 0)
    settle(app, window)
    assert window.compare_page.table.rowCount() == 6


def test_paste_with_header_row(app, window):
    window.table_model.paste_block(0, 0, [["age", "height"], ["10", "140"], ["12", "152"]])
    assert window.table_model.headers[:2] == ["age", "height"]
    assert window.table_model.rows[0][:2] == ["10", "140"]
    assert window.sidebar.y_combo.findText("height") >= 0


def test_export_report_and_plot(app, window, tmp_path, monkeypatch):
    window._load_sample()
    run_fit(app, window)
    report, plot = tmp_path / "r.txt", tmp_path / "p.png"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(report), ""))
    window._export_report()
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(plot), ""))
    window._export_plot()
    assert "REGRESSION REPORT" in report.read_text(encoding="utf-8")
    assert plot.stat().st_size > 1000


def planted_outlier_table(window):
    rng = np.random.default_rng(5)
    x = np.linspace(1, 20, 40)
    y = 3 + 1.5 * x + rng.normal(0, 1.0, 40)
    y[6] += 14
    window.table_model.set_table(["x", "y"], [[f"{a:.3f}", f"{b:.3f}"] for a, b in zip(x, y)])
    return x, y


def test_click_excludes_and_restores_point(app, window):
    x, y = planted_outlier_table(window)
    select_kind(window, ModelKind.LINEAR)
    run_fit(app, window)
    r2_with = window._result.r2
    assert int(np.argmax(window._result.cooks)) == 6

    def click_point(canvas, px, py):
        ax = canvas._axes[0]
        pixel = ax.transData.transform([[px, py]])[0]
        canvas.callbacks.process("button_press_event", MouseEvent("button_press_event", canvas, *pixel, button=1))

    click_point(window.fit_plot, x[6], y[6])
    assert wait_until(app, lambda: window._result.n == 39)
    settle(app, window)
    assert window._excluded == {6}
    assert window._result.r2 > r2_with + 0.05
    assert window.influence_page.excluded_label.text().startswith("Excluded rows (1): 7")

    click_point(window.fit_plot, x[6], y[6])  # the hollow marker restores it
    assert wait_until(app, lambda: window._result.n == 40)
    settle(app, window)
    assert window._excluded == set()


def test_exclusion_that_breaks_the_fit_is_reverted(app, window):
    window.table_model.set_table(["x", "y"], [["1", "1"], ["2", "2.1"], ["3", "2.9"]])
    select_kind(window, ModelKind.LINEAR)
    run_fit(app, window)
    window._toggle_exclusion(0)  # would leave 2 points for 2 parameters
    assert wait_until(app, lambda: bool(window.warnings))
    settle(app, window)
    assert window._excluded == set()
    assert window._result.n == 3


def test_exclusions_cleared_when_table_changes(app, window):
    planted_outlier_table(window)
    select_kind(window, ModelKind.LINEAR)
    run_fit(app, window)
    window._toggle_exclusion(6)
    assert wait_until(app, lambda: window._result.n == 39)
    settle(app, window)
    window.table_model.remove_rows([0])
    assert window._excluded == set()


def test_influence_page_exclude_selected_and_restore(app, window):
    planted_outlier_table(window)
    select_kind(window, ModelKind.LINEAR)
    run_fit(app, window)
    page = window.influence_page
    assert page.table.rowCount() >= 1
    page.table.selectRow(0)
    page.btn_exclude.click()
    assert wait_until(app, lambda: window._result.rows_excluded.size == 1)
    settle(app, window)
    page.btn_restore.click()
    assert wait_until(app, lambda: window._result.rows_excluded.size == 0)
    settle(app, window)


def test_robust_checkbox_changes_table_header(app, window):
    window._load_sample()
    select_kind(window, ModelKind.LINEAR)
    window.sidebar.robust_check.setChecked(True)
    run_fit(app, window)
    assert "HC3" in window.results_page.table.horizontalHeaderItem(2).text()
