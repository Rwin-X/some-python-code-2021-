"""Declarative input form: label above input, typed parsing."""
import re
from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget

from ui.widgets.controls import Combo


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    default: object
    choices: tuple | None = None
    kind: str = "float"  # "float" | "int" | "list" (list of floats)


class FormPanel(QWidget):
    def __init__(self, fields):
        super().__init__()
        self._fields = {f.key: f for f in fields}
        self._widgets = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        for f in fields:
            label = QLabel(f.label)
            label.setObjectName("secondaryLabel")
            label.setWordWrap(True)
            lay.addWidget(label)
            if f.choices:
                w = Combo()
                w.addItems([str(c) for c in f.choices])
            elif f.kind == "list":
                w = QPlainTextEdit()
                w.setFixedHeight(76)
            else:
                w = QLineEdit()
                w.setAlignment(Qt.AlignmentFlag.AlignRight)
            lay.addWidget(w)
            lay.addSpacing(6)
            self._widgets[f.key] = w
            self._set_widget(f, f.default)

    @staticmethod
    def _text(value) -> str:
        if isinstance(value, (list, tuple)):
            return ", ".join(f"{v:g}" if isinstance(v, float) else str(v) for v in value)
        return f"{value:g}" if isinstance(value, float) else str(value)

    def _set_widget(self, f: Field, value) -> None:
        w = self._widgets[f.key]
        if isinstance(w, Combo):
            idx = w.findText(self._text(value))
            if idx >= 0:
                w.setCurrentIndex(idx)
        elif isinstance(w, QPlainTextEdit):
            w.setPlainText(self._text(value))
        else:
            w.setText(self._text(value))

    def set_values(self, data: dict) -> None:
        for key, value in data.items():
            if key in self._fields:
                self._set_widget(self._fields[key], value)

    def values(self) -> dict:
        out = {}
        for key, f in self._fields.items():
            w = self._widgets[key]
            if isinstance(w, Combo):
                text = w.currentText()
                out[key] = self._number(f, text) if f.kind == "int" else text
            elif f.kind == "list":
                tokens = [t for t in re.split(r"[,\s;]+", w.toPlainText().strip()) if t]
                try:
                    out[key] = [float(t) for t in tokens]
                except ValueError:
                    raise ValueError(f"{f.label}: use numbers separated by commas or spaces")
            else:
                out[key] = self._number(f, w.text())
        return out

    @staticmethod
    def _number(f: Field, text: str):
        try:
            x = float(text.replace(",", "").strip())
        except ValueError:
            raise ValueError(f"{f.label}: enter a number")
        if f.kind == "int":
            if x != int(x):
                raise ValueError(f"{f.label}: enter a whole number")
            return int(x)
        return x
