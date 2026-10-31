import json
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication

from datagen.ui.main_window import MainWindow
from datagen.ui.style import build_stylesheet


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    instance.setStyleSheet(build_stylesheet())
    return instance


def wait_until_idle(app, window, timeout=15):
    deadline = time.time() + timeout
    while window._busy and time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)
    app.processEvents()
    assert not window._busy


def test_default_rows_and_config(app, tmp_path):
    window = MainWindow()
    config = window._collect_config()
    assert [f.name for f in config.fields] == ["id", "name", "email", "age", "created_at"]
    assert config.seed is None


def test_add_and_remove_rows(app):
    window = MainWindow()
    window._add_row()
    assert window._rows[-1].name_edit.text() == "field_6"
    window._remove_row(window._rows[0])
    assert len(window._rows) == 5
    assert not window._rows[0].params_edit.isEnabled() or window._rows[0].name_edit.text()


def test_params_disabled_for_types_without_params(app):
    window = MainWindow()
    row = window._rows[1]  # full_name
    assert not row.params_edit.isEnabled()
    row.type_combo.setCurrentIndex(row.type_combo.findData("integer"))
    assert row.params_edit.isEnabled()


def test_generate_end_to_end(app, tmp_path):
    window = MainWindow()
    window.count_spin.setValue(500)
    window.seed_edit.setText("42")
    window.path_edit.setText(str(tmp_path / "result"))
    window._on_generate_clicked()
    assert window._busy
    wait_until_idle(app, window)
    data = json.loads((tmp_path / "result.json").read_text())
    assert len(data) == 500
    assert set(data[0]) == {"id", "name", "email", "age", "created_at"}
    assert window.status.property("state") == "ok"


def test_validation_error_shown(app, tmp_path):
    window = MainWindow()
    window.path_edit.setText(str(tmp_path / "x.json"))
    window._rows[3].params_edit.setText("90, 18")
    window._on_generate_clicked()
    assert not window._busy
    assert window.status.property("state") == "error"
    assert "age" in window.status.text()


def test_cancel(app, tmp_path):
    window = MainWindow()
    window.count_spin.setValue(5_000_000)
    window.path_edit.setText(str(tmp_path / "big.json"))
    window._on_generate_clicked()
    app.processEvents()
    window._on_generate_clicked()  # cancel
    wait_until_idle(app, window, timeout=30)
    assert window.status.text() == "Cancelled"
    assert list(tmp_path.iterdir()) == []
