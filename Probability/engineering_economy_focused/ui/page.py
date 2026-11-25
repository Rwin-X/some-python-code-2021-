"""Base calculator page: form on the left, results on the right, work off the UI thread."""
from dataclasses import dataclass, field

from PyQt6.QtCore import Qt, QThreadPool, pyqtSignal
from PyQt6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QPushButton,
                             QVBoxLayout, QWidget)

from ui.i18n import plain, rich
from ui.widgets.form import FormPanel
from ui.widgets.tables import MAX_FIT_ROWS, make_table
from ui.worker import Worker


@dataclass
class Output:
    items: list = field(default_factory=list)    # (label, value) pairs
    tables: list = field(default_factory=list)   # (title, columns, rows)
    data: object = None                           # page-specific payload (e.g. chart data)


def clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            clear_layout(item.layout())


class Page(QWidget):
    title = ""
    section = ""        # key in the dataset JSON
    fields = ()
    SHARED_KEYS = ("cash_flows", "marr")  # inputs kept in sync across pages
    shared_changed = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._workers: set = set()   # strong refs: a runnable must outlive its thread
        self._seq = 0                # only the newest run may update the page
        self.last_output: Output | None = None

        outer = QHBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 12)
        outer.setSpacing(32)

        left = QWidget()
        left.setFixedWidth(290)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(14)
        heading = QLabel(rich(self.title, 13))
        heading.setTextFormat(Qt.TextFormat.RichText)
        heading.setWordWrap(True)
        heading.setObjectName("pageTitle")
        lv.addWidget(heading)
        self.form = FormPanel(self.fields)
        lv.addWidget(self.form)
        self.run_btn = QPushButton(plain("Calculate"))
        self.run_btn.setObjectName("primaryAction")
        self.run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.run_btn.clicked.connect(lambda: self.run())
        lv.addWidget(self.run_btn)
        self.status = QLabel("")
        self.status.setObjectName("status")
        self.status.setWordWrap(True)
        lv.addWidget(self.status)
        lv.addStretch()
        outer.addWidget(left)

        right = self._right = QVBoxLayout()
        right.setSpacing(16)
        self.build_top(right)
        self.items_box = QWidget()
        self.items = QGridLayout(self.items_box)
        self.items.setContentsMargins(0, 0, 0, 0)
        self.items.setHorizontalSpacing(28)
        self.items.setVerticalSpacing(6)
        right.addWidget(self.items_box, 0, Qt.AlignmentFlag.AlignLeft)
        self.tables = QVBoxLayout()
        self.tables.setSpacing(8)
        right.addLayout(self.tables, 0)
        self.build_bottom(right)
        outer.addLayout(right, 1)

    # ---- hooks for subclasses -------------------------------------------------
    def build_top(self, layout) -> None:
        pass

    def build_bottom(self, layout) -> None:
        pass

    def after_render(self, out: Output) -> None:
        pass

    def values(self) -> dict:
        return self.form.values()

    def compute(self, v: dict) -> Output:  # runs on a worker thread: no widget access
        raise NotImplementedError

    def load(self, data: dict) -> None:
        self.form.set_values(data)

    # ---- dataset --------------------------------------------------------------
    def apply_dataset(self, dataset: dict) -> None:
        data = dict(dataset.get("shared", {}))
        block = dataset.get(self.section) if self.section else None
        if isinstance(block, dict):
            data.update(block.get("input", {}))
        mine = {k: v for k, v in data.items() if k in self.form._fields or self._accepts(k)}
        if mine:
            self.load(mine)
            self.run(emit=False)

    def _accepts(self, key: str) -> bool:
        return False

    def sync(self, data: dict) -> None:
        """Adopt shared inputs (cash flows, MARR) edited on another page."""
        mine = {k: v for k, v in data.items() if k in self.form._fields}
        if mine:
            self.load(mine)
            self.run(emit=False)

    # ---- execution ------------------------------------------------------------
    def set_status(self, text: str, error: bool = False) -> None:
        self.status.setText(text)
        self.status.setProperty("error", error)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def run(self, emit: bool = True) -> None:
        try:
            v = self.values()
        except ValueError as exc:
            self.set_status(str(exc), True)
            return
        self.set_status("")
        if emit:
            shared = {k: v[k] for k in self.SHARED_KEYS if k in v}
            if shared:
                self.shared_changed.emit(shared)
        self._seq += 1
        seq = self._seq
        worker = Worker(self.compute, v)
        worker.signals.done.connect(lambda out, w=worker, s=seq: self._finish(w, s, out=out))
        worker.signals.failed.connect(lambda msg, w=worker, s=seq: self._finish(w, s, error=msg))
        self._workers.add(worker)
        self.run_btn.setEnabled(False)
        QThreadPool.globalInstance().start(worker)

    def _finish(self, worker, seq, out=None, error=None) -> None:
        self._workers.discard(worker)
        if not self._workers:
            self.run_btn.setEnabled(True)
        if seq != self._seq:  # stale result from an older run
            return
        if error is not None:
            self.set_status(error, True)
        else:
            self.last_output = out
            self.render(out)

    def render(self, out: Output) -> None:
        clear_layout(self.items)
        clear_layout(self.tables)
        for r, (k, val) in enumerate(out.items):
            a = QLabel(rich(k))
            a.setTextFormat(Qt.TextFormat.RichText)
            a.setObjectName("secondaryLabel")
            b = QLabel(plain(val))
            b.setObjectName("valueLabel")
            b.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.items.addWidget(a, r, 0)
            self.items.addWidget(b, r, 1)
        for title, cols, rows in out.tables:
            if title:
                t = QLabel(plain(title))
                t.setObjectName("tertiaryLabel")
                self.tables.addWidget(t)
            self.tables.addWidget(make_table(cols, rows), 1)
        grows = any(len(rows) > MAX_FIT_ROWS for _t, _c, rows in out.tables)
        if not grows:
            self.tables.addStretch(1)  # keep short tables packed at the top
        self._right.setStretchFactor(self.tables, 1 if grows else 0)
        self.after_render(out)
