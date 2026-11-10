#!/usr/bin/env python3
"""
DataDeck - a minimal data manager with a live operation feed.

Stdlib only (Python 3.9+ with tkinter). No pandas, nothing to install.

    python datadeck.py [file.csv | file.tsv | file.json]

Every change to the data is an *operation*: it is snapshotted (undo/redo),
applied atomically (a failing operation leaves the data untouched), and
reported live in the side panel together with its exact effect.
"""
from __future__ import annotations

import csv
import io
import json
import math
import os
import re
import statistics
import sys
import time
import tkinter as tk
from collections import Counter
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

APP = "DataDeck"
MAX_ROWS_SHOWN = 5000          # display cap only; operations always use all rows
HISTORY_LIMIT = 40             # max undo snapshots kept in memory
HISTORY_CELLS = 5_000_000      # ...and a cell budget across all snapshots (oldest dropped first)
ALL = "(all columns)"
NULLS = {"", "na", "n/a", "null", "none", "nan"}

BG, PANEL, LINE = "#0b0d0e", "#111416", "#1e2428"
FG, DIM, DIM2 = "#cfd8dc", "#5f6c72", "#8a989e"
ACCENT, SEL = "#3dff8f", "#143527"
WARN, ERR = "#e6c04f", "#ff5c5c"


# --------------------------------------------------------------------------- #
#  Pure helpers (no GUI)                                                      #
# --------------------------------------------------------------------------- #
class OpError(Exception):
    """A recoverable, user-facing failure inside an operation."""


_NUM = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")
_INT = re.compile(r"^[+-]?\d+$")
_JSON_INT = re.compile(r"^-?(0|[1-9]\d*)$")


def is_null(s: str) -> bool:
    return s == "" or s.strip().lower() in NULLS


def to_num(s: str):
    s = s.strip()
    if _NUM.match(s):
        v = float(s)
        if math.isfinite(v):
            return v
    return None


def fmt_num(x: float) -> str:
    if not math.isfinite(x):          # e.g. a mean that overflowed
        return str(x)
    if x == int(x) and abs(x) < 1e15:
        return str(int(x))
    return f"{x:.10g}"


_WORD = re.compile(r"\S+")


def title_case(s: str) -> str:
    """Capitalise each word but keep the original spacing (string.capwords collapses it)."""
    return _WORD.sub(lambda m: m.group(0).capitalize(), s)


def clip(s: str, n: int = 28) -> str:
    s = s.replace("\n", "\u23ce")
    return f'"{s[:n]}\u2026"' if len(s) > n else f'"{s}"'


def trunc(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "\u2026"


def unique_names(names):
    out, seen = [], set()
    for i, n in enumerate(names):
        base = (n or "").strip() or f"col_{i + 1}"
        name, k = base, 2
        while name.casefold() in seen:
            name, k = f"{base}_{k}", k + 1
        seen.add(name.casefold())
        out.append(name)
    return out


def json_cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, bool):
        return "true" if v else "false"
    return json.dumps(v, ensure_ascii=False)


def json_value(s: str):
    """Lossless-only typing: a cell becomes a JSON number only if it round-trips."""
    if s == "":
        return None
    if s in ("true", "false"):          # json_cell() writes booleans this way: keep them booleans
        return s == "true"
    if _JSON_INT.match(s):
        return int(s)
    try:
        f = float(s)
        if math.isfinite(f) and repr(f) == s:
            return f
    except ValueError:
        pass
    return s


def read_table(path: str):
    """Return (columns, rows, info). Row 1 of CSV/TSV is always the header."""
    ext = os.path.splitext(path)[1].lower()
    with open(path, "rb") as fh:
        data = fh.read()
    text, enc = "", "utf-8"
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if not text.strip():
        raise OpError("file is empty")

    if ext == ".json":
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as e:
            raise OpError(f"invalid JSON: {e}")
        if not (isinstance(obj, list) and obj and all(isinstance(o, dict) for o in obj)):
            raise OpError("JSON must be a non-empty array of objects")
        keys = list(dict.fromkeys(k for o in obj for k in o))
        rows = [[json_cell(o.get(k)) for k in keys] for o in obj]
        return unique_names(keys), rows, f"{enc} \u00b7 json"

    delim = "\t" if ext == ".tsv" else ","
    if ext != ".tsv":
        try:
            delim = csv.Sniffer().sniff(text[:65536], delimiters=",;\t|").delimiter
        except csv.Error:
            pass
    csv.field_size_limit(2**31 - 1)
    try:
        table = [r for r in csv.reader(io.StringIO(text, newline=""), delimiter=delim) if r]
    except csv.Error as e:
        raise OpError(f"CSV parse error: {e}")
    if not table:
        raise OpError("no rows found")
    width = max(map(len, table))
    header = unique_names(table[0] + [""] * (width - len(table[0])))
    rows = [r + [""] * (width - len(r)) for r in table[1:]]
    return header, rows, f"{enc} \u00b7 delimiter {delim!r}"


def write_table(path: str, cols, rows) -> str:
    """Atomic write (temp file + replace). Returns an info string."""
    ext = os.path.splitext(path)[1].lower()
    tmp = f"{path}.tmp"
    try:
        if ext == ".json":
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump([{c: json_value(v) for c, v in zip(cols, r)} for r in rows],
                          fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            info = "utf-8 \u00b7 json"
        else:
            delim = "\t" if ext == ".tsv" else ","
            with open(tmp, "w", encoding="utf-8-sig", newline="") as fh:
                w = csv.writer(fh, delimiter=delim, lineterminator="\n")
                w.writerow(cols)
                w.writerows(rows)
            info = "utf-8 (BOM)"
        os.replace(tmp, path)
        return info
    except OSError as e:
        raise OpError(str(e))
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


# --------------------------------------------------------------------------- #
#  Widgets                                                                    #
# --------------------------------------------------------------------------- #
class Flat(tk.Label):
    """Flat text button (a Label, so colours work on every platform)."""

    def __init__(self, master, text, command, font, bg=BG):
        super().__init__(master, text=text, bg=bg, fg=FG, font=font,
                         padx=12, pady=7, cursor="hand2")
        self.base, self.command, self.enabled = bg, command, True
        self.bind("<Enter>", lambda e: self.enabled and self.configure(bg=LINE, fg=ACCENT))
        self.bind("<Leave>", lambda e: self.configure(bg=self.base, fg=FG if self.enabled else DIM))
        self.bind("<Button-1>", lambda e: self.enabled and self.command())

    def set_enabled(self, on: bool):
        self.enabled = on
        self.configure(bg=self.base, fg=FG if on else DIM, cursor="hand2" if on else "arrow")


class Form(tk.Toplevel):
    """Modal parameter dialog. `result` is a dict, or None if cancelled."""

    def __init__(self, app, title, fields, ok="Apply"):
        super().__init__(app)
        self.withdraw()
        self.title(title)
        self.configure(bg=PANEL)
        self.resizable(False, False)
        self.transient(app)
        self.result, self.vars = None, {}

        body = tk.Frame(self, bg=PANEL, padx=22, pady=18)
        body.pack(fill="both")
        tk.Label(body, text=title.upper(), bg=PANEL, fg=ACCENT, font=app.fb).grid(
            row=0, column=0, sticky="w", pady=(0, 14))

        first = None
        for n, f in enumerate(fields, start=1):
            kind = f.get("kind", "entry")
            if kind != "check":
                tk.Label(body, text=f["label"].lower(), bg=PANEL, fg=DIM, font=app.fs).grid(
                    row=2 * n - 1, column=0, sticky="w")
            if kind == "choice":
                var = tk.StringVar(value=f.get("default") or f["options"][0])
                w = ttk.Combobox(body, textvariable=var, values=f["options"],
                                 state="readonly", width=34, font=app.f)
            elif kind == "check":
                var = tk.BooleanVar(value=bool(f.get("default")))
                w = tk.Checkbutton(body, text=f["label"], variable=var, bg=PANEL, fg=FG,
                                   selectcolor=BG, activebackground=PANEL,
                                   activeforeground=ACCENT, font=app.fs, bd=0,
                                   highlightthickness=0, anchor="w")
            else:
                var = tk.StringVar(value=f.get("default", ""))
                w = tk.Entry(body, textvariable=var, width=36, bg=BG, fg=FG,
                             insertbackground=ACCENT, relief="flat", font=app.f,
                             highlightthickness=1, highlightbackground=LINE,
                             highlightcolor=ACCENT)
            w.grid(row=2 * n, column=0, sticky="ew", pady=(3, 12),
                   ipady=4 if kind == "entry" else 0)
            self.vars[f["key"]] = var
            first = first or w

        row = tk.Frame(body, bg=PANEL)
        row.grid(row=2 * len(fields) + 1, column=0, sticky="e")
        Flat(row, "Cancel", self.destroy, app.f, bg=PANEL).pack(side="left")
        Flat(row, ok.upper(), self.accept, app.fb, bg=PANEL).pack(side="left")

        self.bind("<Return>", lambda e: self.accept())
        self.bind("<Escape>", lambda e: self.destroy())
        self.update_idletasks()
        x = app.winfo_rootx() + (app.winfo_width() - self.winfo_width()) // 2
        y = app.winfo_rooty() + (app.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.deiconify()
        self.wait_visibility()
        self.grab_set()
        if first is not None:
            first.focus_set()
        self.wait_window(self)

    def accept(self):
        self.result = {k: v.get() for k, v in self.vars.items()}
        self.destroy()


# --------------------------------------------------------------------------- #
#  Application                                                                #
# --------------------------------------------------------------------------- #
class App(tk.Tk):
    def __init__(self, path: str | None = None):
        super().__init__()
        self.cols: list[str] = []
        self.rows: list[list[str]] = []
        self.path: str | None = None
        self.dirty = False
        self.active = 0                          # active column index
        self.sort_state: tuple[int, bool] | None = None
        self.undo_stack: list = []
        self.redo_stack: list = []
        self.match_count = 0
        self._edit = None
        self._after_filter = None
        self._after_panel = None
        self._last_filter = ""
        self._mute_filter = False
        self._rendered_cols: list[str] | None = None   # to keep manual column widths
        self.rev = 0                                   # bumped on every data change
        self._stats = (-1, 0, 0)                       # (rev, empty cells, duplicate rows)
        self._prof_key = None
        self._prof_val = ("\u2014", [])

        self._fonts()
        self._style()
        self._build()
        self._keys()
        self.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.render()
        self.refresh_panel()
        self.log("sys", "ready", "Open a file or create a new dataset to begin.")
        if path:
            self.after(60, lambda: self.open_path(path))

    # ------------------------------------------------------------- setup --- #
    def _fonts(self):
        fams = set(tkfont.families())
        fam = next((f for f in ("JetBrains Mono", "Cascadia Mono", "Consolas", "SF Mono",
                                "Menlo", "DejaVu Sans Mono", "Liberation Mono",
                                "Courier New") if f in fams), "Courier")
        self.f = tkfont.Font(family=fam, size=10)
        self.fb = tkfont.Font(family=fam, size=10, weight="bold")
        self.fs = tkfont.Font(family=fam, size=9)
        self.fsb = tkfont.Font(family=fam, size=9, weight="bold")
        self.cw = self.f.measure("0")
        self.fam = fam

    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Treeview", background=BG, fieldbackground=BG, foreground=FG,
                    rowheight=24, borderwidth=0, font=self.f)
        s.map("Treeview", background=[("selected", SEL)], foreground=[("selected", ACCENT)])
        s.configure("Treeview.Heading", background=PANEL, foreground=DIM2, relief="flat",
                    borderwidth=0, font=self.fsb, padding=(8, 7))
        s.map("Treeview.Heading", background=[("active", LINE)], foreground=[("active", ACCENT)])
        s.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        for o, st in (("Vertical", "ns"), ("Horizontal", "ew")):
            s.layout(f"{o}.TScrollbar", [(f"{o}.Scrollbar.trough", {"sticky": st, "children": [
                (f"{o}.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
            s.configure(f"{o}.TScrollbar", background=LINE, troughcolor=BG, bordercolor=BG,
                        lightcolor=LINE, darkcolor=LINE, gripcount=0, width=10)
            s.map(f"{o}.TScrollbar", background=[("active", DIM)])
        s.configure("TCombobox", fieldbackground=BG, background=LINE, foreground=FG,
                    arrowcolor=DIM2, bordercolor=LINE, lightcolor=BG, darkcolor=BG,
                    selectbackground=BG, selectforeground=ACCENT, padding=4)
        s.map("TCombobox", fieldbackground=[("readonly", BG)], foreground=[("readonly", FG)],
              selectbackground=[("readonly", BG)], selectforeground=[("readonly", ACCENT)])
        self.option_add("*TCombobox*Listbox.background", PANEL)
        self.option_add("*TCombobox*Listbox.foreground", FG)
        self.option_add("*TCombobox*Listbox.selectBackground", SEL)
        self.option_add("*TCombobox*Listbox.selectForeground", ACCENT)
        self.option_add("*TCombobox*Listbox.font", self.f)

    def acc(self, key: str) -> str:
        return f"\u2318{key}" if sys.platform == "darwin" else f"Ctrl+{key}"

    def _build(self):
        self.title(APP)
        self.geometry("1280x740")
        self.minsize(960, 540)
        self.configure(bg=BG)

        # toolbar -----------------------------------------------------------
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x")
        tk.Frame(self, bg=LINE, height=1).pack(fill="x")

        def popup(menu, w):
            try:
                menu.tk_popup(w.winfo_rootx(), w.winfo_rooty() + w.winfo_height())
            finally:
                menu.grab_release()

        def dropdown(text, items):
            m = tk.Menu(self, tearoff=0, bg=PANEL, fg=FG, activebackground=SEL,
                        activeforeground=ACCENT, bd=0, relief="flat", font=self.f)
            for it in items:
                if it is None:
                    m.add_separator()
                else:
                    m.add_command(label=it[0], command=it[1], accelerator=it[2] if len(it) > 2 else "")
            b = Flat(bar, text + " \u25be", lambda: popup(m, b), self.f)
            b.pack(side="left")

        dropdown("File", [
            ("New\u2026", self.new_dataset, self.acc("N")),
            ("Open\u2026", self.open_dialog, self.acc("O")),
            None,
            ("Save", self.save, self.acc("S")),
            ("Save as\u2026", self.save_as, self.acc("Shift+S")),
            None,
            ("Quit", self.quit_app)])
        self.btn_undo = Flat(bar, "Undo", self.undo, self.f)
        self.btn_undo.pack(side="left")
        self.btn_redo = Flat(bar, "Redo", self.redo, self.f)
        self.btn_redo.pack(side="left")
        g = self.guard
        dropdown("Rows", [
            ("Add row", g(self.op_add_row), "Insert"),
            ("Delete selected", g(self.op_delete_rows), "Delete"),
            ("Delete rows matching filter\u2026", g(self.op_delete_matching)),
            None,
            ("Sort\u2026", g(self.op_sort)),
            ("Drop duplicates\u2026", g(self.op_dedupe)),
            ("Drop empty rows", g(self.op_drop_empty))])
        dropdown("Columns", [
            ("Add column\u2026", g(self.op_add_col)),
            ("Rename column\u2026", g(self.op_rename_col)),
            ("Delete column\u2026", g(self.op_delete_col))])
        dropdown("Clean", [
            ("Trim whitespace\u2026", g(self.op_trim)),
            ("Fill missing values\u2026", g(self.op_fill)),
            ("Change case\u2026", g(self.op_case)),
            ("Find & replace\u2026", g(self.op_replace), self.acc("H"))])

        fbox = tk.Frame(bar, bg=BG)
        fbox.pack(side="right", padx=(0, 12))
        tk.Label(fbox, text="filter", bg=BG, fg=DIM, font=self.fs).pack(side="left", padx=(0, 8))
        self.filter_var = tk.StringVar()
        self.filter_entry = tk.Entry(fbox, textvariable=self.filter_var, width=32, bg=PANEL, fg=FG,
                                     insertbackground=ACCENT, relief="flat", font=self.f,
                                     highlightthickness=1, highlightbackground=LINE,
                                     highlightcolor=ACCENT)
        self.filter_entry.pack(side="left", ipady=3)
        self.filter_var.trace_add("write", self._on_filter_change)

        # status bar --------------------------------------------------------
        status = tk.Frame(self, bg=PANEL)
        status.pack(side="bottom", fill="x")
        tk.Frame(self, bg=LINE, height=1).pack(side="bottom", fill="x")
        tk.Label(status, bg=PANEL, fg=DIM, font=self.fs, padx=12, pady=5,
                 text="double-click cell \u2192 edit  \u00b7  header \u2192 sort  \u00b7  "
                      "column:text \u2192 filter one column").pack(side="left")
        self.shown = tk.Label(status, bg=PANEL, fg=DIM2, font=self.fs, padx=12)
        self.shown.pack(side="right")

        # main --------------------------------------------------------------
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True)
        side = tk.Frame(main, bg=PANEL, width=400)
        side.pack(side="right", fill="y")
        side.pack_propagate(False)
        tk.Frame(main, bg=LINE, width=1).pack(side="right", fill="y")
        left = tk.Frame(main, bg=BG)
        left.pack(side="left", fill="both", expand=True)

        self.tree = ttk.Treeview(left, show="tree headings", selectmode="extended")
        vsb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(left, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.hint = tk.Label(left, bg=BG, fg=DIM, font=self.f, justify="center",
                             text=f"no dataset\n\n{self.acc('O')}  open\n{self.acc('N')}  new")
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<ButtonRelease-1>", self.on_click)
        for k in ("<Delete>", "<BackSpace>"):
            self.tree.bind(k, lambda e: self.guard(self.op_delete_rows)())
        self.tree.bind("<Insert>", lambda e: self.guard(self.op_add_row)())
        mod = "Command" if sys.platform == "darwin" else "Control"
        self.tree.bind(f"<{mod}-c>", self.copy_rows)

        # side panel --------------------------------------------------------
        self.section(side, "DATASET")
        grid = tk.Frame(side, bg=PANEL)
        grid.pack(fill="x", padx=16)
        self.kv = {}
        for r, key in enumerate(("file", "rows", "columns", "empty cells", "duplicates",
                                 "state", "history")):
            tk.Label(grid, text=key, bg=PANEL, fg=DIM, font=self.fs, anchor="w",
                     width=12).grid(row=r, column=0, sticky="w")
            v = tk.StringVar()
            tk.Label(grid, textvariable=v, bg=PANEL, fg=FG, font=self.f,
                     anchor="w").grid(row=r, column=1, sticky="w")
            self.kv[key] = v

        self.section(side, "COLUMN")
        self.col_title = tk.Label(side, bg=PANEL, fg=ACCENT, font=self.fb, anchor="w")
        self.col_title.pack(fill="x", padx=16, pady=(0, 4))
        self.prof = tk.Text(side, height=9, bg=PANEL, fg=FG, font=self.f, bd=0,
                            highlightthickness=0, state="disabled", cursor="arrow", wrap="none")
        self.prof.tag_configure("k", foreground=DIM, font=self.fs)
        self.prof.pack(fill="x", padx=16)

        self.section(side, "OPERATION LOG", action=("clear", self.clear_log))
        lf = tk.Frame(side, bg=PANEL)
        lf.pack(fill="both", expand=True, padx=(16, 6), pady=(0, 12))
        self.logbox = tk.Text(lf, bg=PANEL, fg=FG, font=self.fs, bd=0, highlightthickness=0,
                              wrap="word", state="disabled", cursor="arrow", padx=0, pady=0)
        sb = ttk.Scrollbar(lf, command=self.logbox.yview)
        self.logbox.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.logbox.pack(side="left", fill="both", expand=True)
        indent = self.fs.measure("00:00:00  ")
        self.logbox.tag_configure("ts", foreground=DIM)
        for tag, color in (("ok", ACCENT), ("view", DIM2), ("warn", WARN),
                           ("err", ERR), ("sys", DIM)):
            self.logbox.tag_configure(tag, foreground=color, font=self.fsb)
        self.logbox.tag_configure("detail", foreground=FG, lmargin1=indent, lmargin2=indent,
                                  spacing3=9)

    def section(self, parent, title, action=None):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=16, pady=(16, 6))
        tk.Label(row, text=title, bg=PANEL, fg=DIM, font=self.fs).pack(side="left")
        if action:
            lbl = tk.Label(row, text=action[0], bg=PANEL, fg=DIM, font=self.fs, cursor="hand2")
            lbl.pack(side="right")
            lbl.bind("<Button-1>", lambda e: action[1]())
            lbl.bind("<Enter>", lambda e: lbl.configure(fg=ACCENT))
            lbl.bind("<Leave>", lambda e: lbl.configure(fg=DIM))

    def _keys(self):
        mod = "Command" if sys.platform == "darwin" else "Control"

        def bind(seq, fn, typing_ok=False):
            def handler(e):
                if not typing_ok:
                    try:
                        w = self.focus_get()
                    except KeyError:
                        w = None
                    if isinstance(w, (tk.Entry, ttk.Entry, ttk.Combobox)):
                        return None
                fn()
                return "break"
            self.bind(f"<{mod}-{seq}>", handler)

        bind("o", self.open_dialog, True)
        bind("n", self.new_dataset, True)
        bind("s", self.save, True)
        bind("S", self.save_as, True)
        bind("z", self.undo)
        bind("y", self.redo)
        bind("Z", self.redo)
        bind("h", self.guard(self.op_replace), True)
        bind("f", lambda: (self.filter_entry.focus_set(), self.filter_entry.select_range(0, "end")), True)

    # ------------------------------------------------------------- guard --- #
    def guard(self, fn):
        def inner(*_):
            if not self.cols:
                self.log("warn", "no data", "Open a file or create a dataset first.")
                return
            fn()
        return inner

    def ask(self, title, fields, ok="Apply"):
        return Form(self, title, fields, ok).result

    # --------------------------------------------------------------- log --- #
    def log(self, kind, op, detail="", delta=""):
        t = self.logbox
        t.configure(state="normal")
        t.insert("end", time.strftime("%H:%M:%S") + "  ", "ts")
        t.insert("end", op.upper() + "\n", kind)
        line = detail + (("  \u00b7  " if detail else "") + delta if delta else "")
        t.insert("end", (line or "ok") + "\n", "detail")
        if int(t.index("end-1c").split(".")[0]) > 1500:
            t.delete("1.0", "401.0")
        t.see("end")
        t.configure(state="disabled")

    def clear_log(self):
        self.logbox.configure(state="normal")
        self.logbox.delete("1.0", "end")
        self.logbox.configure(state="disabled")

    # ------------------------------------------------------- operation core #
    def snapshot(self):
        return (self.cols[:], [r[:] for r in self.rows])

    def restore(self, snap):
        self.cols, self.rows = snap          # snapshots are single-owner: no copy needed

    def run(self, name, op, keep=()) -> bool:
        """Run `op` atomically. `op()` mutates the data and returns (detail, affected)."""
        self.end_edit(True)                  # never lose a half-typed cell edit
        before = self.snapshot()
        nr, nc = len(self.rows), len(self.cols)
        try:
            detail, affected = op()
        except OpError as e:
            self.restore(before)
            self.log("err", name, str(e))
            return False
        except Exception as e:  # noqa: BLE001 - never lose the user's data
            self.restore(before)
            self.log("err", name, f"{type(e).__name__}: {e}")
            return False
        if not affected:
            self.restore(before)             # a no-op must leave the data exactly as it was
            self.log("warn", name, detail or "nothing to change")
            return False
        self.undo_stack.append((name, before))
        self._trim_history()
        self.redo_stack.clear()
        if name != "SORT":
            self.sort_state = None
        self.dirty = True
        self.rev += 1
        delta = []
        if len(self.rows) != nr:
            delta.append(f"rows {nr:,} \u2192 {len(self.rows):,}")
        if len(self.cols) != nc:
            delta.append(f"cols {nc} \u2192 {len(self.cols)}")
        self.log("ok", name, detail, " \u00b7 ".join(delta))
        self.active = max(0, min(self.active, len(self.cols) - 1))
        self.render(keep)
        self.schedule_panel()
        self.update_title()
        return True

    def _trim_history(self):
        """Bound undo memory: at most HISTORY_LIMIT snapshots and HISTORY_CELLS cells."""
        del self.undo_stack[:-HISTORY_LIMIT]

        def cost(entry):
            cols, rows = entry[1]
            return len(rows) * max(len(cols), 1)
        total = sum(map(cost, self.undo_stack))
        while len(self.undo_stack) > 1 and total > HISTORY_CELLS:
            total -= cost(self.undo_stack.pop(0))

    def _history_step(self, src, dst, label):
        if not src:
            return
        name, snap = src.pop()
        nr, nc = len(self.rows), len(self.cols)
        dst.append((name, self.snapshot()))
        self.restore(snap)
        self.sort_state = None
        self.dirty = True
        self.rev += 1
        self.active = max(0, min(self.active, len(self.cols) - 1))
        delta = []
        if len(self.rows) != nr:
            delta.append(f"rows {nr:,} \u2192 {len(self.rows):,}")
        if len(self.cols) != nc:
            delta.append(f"cols {nc} \u2192 {len(self.cols)}")
        self.log("ok", label, name.lower(), " \u00b7 ".join(delta))
        self._trim_history()
        self.render()
        self.schedule_panel()
        self.update_title()

    def undo(self):
        self._history_step(self.undo_stack, self.redo_stack, "undo")

    def redo(self):
        self._history_step(self.redo_stack, self.undo_stack, "redo")

    # ----------------------------------------------------------- file ops --- #
    def _reset(self, path=None):
        self.path, self.dirty, self.active, self.sort_state = path, False, 0, None
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.clear_filter()
        self._rendered_cols = None           # new data: auto-size the columns again
        self.rev += 1

    def clear_filter(self):
        """Empty the filter box without a delayed, redundant re-render (which would
        drop the selection or an open cell editor)."""
        if self._after_filter:
            self.after_cancel(self._after_filter)
            self._after_filter = None
        self._mute_filter = True
        try:
            self.filter_var.set("")
        finally:
            self._mute_filter = False
        self._last_filter = ""

    def confirm_discard(self) -> bool:
        self.end_edit(True)
        if not self.dirty:
            return True
        ans = messagebox.askyesnocancel(APP, "Save changes before continuing?")
        if ans is None:
            return False
        return self.save() if ans else True

    def new_dataset(self):
        if not self.confirm_discard():
            return
        f = self.ask("New dataset", [dict(key="names", label="Column names (comma-separated)",
                                          default="id, name, value")], ok="Create")
        if not f:
            return
        names = [n for n in f["names"].split(",") if n.strip()]
        if not names:
            self.log("warn", "new", "At least one column name is required.")
            return
        self.cols, self.rows = unique_names(names), []
        self._reset()
        self.log("ok", "new", f"{len(self.cols)} column(s): " + ", ".join(self.cols))
        self.render()
        self.schedule_panel()
        self.update_title()

    def open_dialog(self):
        if not self.confirm_discard():
            return
        p = filedialog.askopenfilename(filetypes=[("Data files", "*.csv *.tsv *.json"),
                                                  ("All files", "*.*")])
        if p:
            self.open_path(p)

    def open_path(self, path):
        try:
            cols, rows, info = read_table(path)
        except (OpError, OSError) as e:
            self.log("err", "open", f"{os.path.basename(path)}: {e}")
            return
        self.cols, self.rows = cols, rows
        self._reset(path)
        self.log("ok", "open", f"{os.path.basename(path)} \u00b7 {len(rows):,} rows \u00d7 "
                               f"{len(cols)} cols \u00b7 {info}")
        self.render()
        self.schedule_panel()
        self.update_title()

    def save(self) -> bool:
        self.end_edit(True)
        if not self.cols:
            self.log("warn", "save", "Nothing to save.")
            return False
        return self._write(self.path) if self.path else self.save_as()

    def save_as(self) -> bool:
        self.end_edit(True)
        if not self.cols:
            self.log("warn", "save", "Nothing to save.")
            return False
        p = filedialog.asksaveasfilename(
            defaultextension=".csv", initialfile=os.path.basename(self.path or "data.csv"),
            filetypes=[("CSV", "*.csv"), ("TSV", "*.tsv"), ("JSON", "*.json")])
        return self._write(p) if p else False

    def _write(self, p) -> bool:
        try:
            info = write_table(p, self.cols, self.rows)
        except OpError as e:
            self.log("err", "save", str(e))
            return False
        self.path, self.dirty = p, False
        self.log("ok", "save", f"{os.path.basename(p)} \u00b7 {len(self.rows):,} rows \u00b7 {info}")
        self.update_title()
        self.schedule_panel()
        return True

    def quit_app(self):
        if self.confirm_discard():
            self.destroy()

    def update_title(self):
        name = os.path.basename(self.path) if self.path else "untitled"
        mark = "\u25cf " if self.dirty else ""   # no backslash inside f-string braces (<3.12)
        self.title(f"{mark}{name} \u2014 {APP}")

    # ------------------------------------------------------- table / view --- #
    def visible_indices(self):
        q = self.filter_var.get().strip()
        if not q:
            return list(range(len(self.rows)))
        col = None
        if ":" in q:
            head, _, tail = q.partition(":")
            for i, c in enumerate(self.cols):
                if c.casefold() == head.strip().casefold():
                    col, q = i, tail.strip()
                    break
        q = q.casefold()
        if col is None:
            return [i for i, r in enumerate(self.rows) if any(q in c.casefold() for c in r)]
        return [i for i, r in enumerate(self.rows) if q in r[col].casefold()]

    def render(self, keep=()):
        self.end_edit(False)
        t = self.tree
        yview = t.yview()[0]
        old_w = {}
        if self._rendered_cols == self.cols:
            old_w = {i: int(t.column(f"c{i}", "width")) for i in range(len(self.cols))}
        t.delete(*t.get_children())
        ids = [f"c{i}" for i in range(len(self.cols))]
        t.configure(columns=ids)
        sample = self.rows[:200]
        for i, name in enumerate(self.cols):
            arrow = ""
            if self.sort_state and self.sort_state[0] == i:
                arrow = "  \u25b2" if self.sort_state[1] else "  \u25bc"
            t.heading(ids[i], text=name + arrow, anchor="w",
                      command=lambda i=i: self.sort_by_header(i))
            chars = max([len(name) + 5] + [len(r[i]) for r in sample])
            t.column(ids[i], width=old_w.get(i) or max(70, min(300, chars * self.cw + 18)),
                     minwidth=50, anchor="w", stretch=False)
        self._rendered_cols = self.cols[:]
        t.heading("#0", text="#")
        t.column("#0", width=62, minwidth=40, anchor="e", stretch=False)

        match = self.visible_indices()
        self.match_count = len(match)
        for ri in match[:MAX_ROWS_SHOWN]:
            t.insert("", "end", iid=str(ri), text=str(ri + 1), values=self.rows[ri])

        present = [str(i) for i in keep if t.exists(str(i))]
        if present:
            t.selection_set(present)
            t.see(present[0])
        else:
            t.yview_moveto(yview)

        if self.cols:
            self.hint.place_forget()
        else:
            self.hint.place(relx=0.5, rely=0.5, anchor="center")
        txt = f"{min(self.match_count, MAX_ROWS_SHOWN):,} of {len(self.rows):,} rows"
        if self.match_count > MAX_ROWS_SHOWN:
            txt += f"  \u00b7  display capped at {MAX_ROWS_SHOWN:,} \u2014 refine the filter"
        self.shown.configure(text=txt)

    def _on_filter_change(self, *_):
        if self._mute_filter:
            return
        if self._after_filter:
            self.after_cancel(self._after_filter)
        self._after_filter = self.after(350, self._apply_filter)

    def _apply_filter(self):
        self._after_filter = None
        q = self.filter_var.get().strip()
        self.render()
        self.schedule_panel()
        if q != self._last_filter:
            if q:
                self.log("view", "filter",
                         f'"{q}" \u2192 {self.match_count:,} of {len(self.rows):,} rows')
            else:
                self.log("view", "filter", "cleared")
            self._last_filter = q

    def sort_by_header(self, ci):
        if not self.cols:
            return
        self.active = ci
        asc = not (self.sort_state and self.sort_state[0] == ci and self.sort_state[1])
        self.do_sort(ci, asc, "auto")

    def on_click(self, e):
        if self.tree.identify_region(e.x, e.y) in ("cell", "tree"):
            ci = int(self.tree.identify_column(e.x)[1:]) - 1
            if 0 <= ci < len(self.cols) and ci != self.active:
                self.active = ci
                self.schedule_panel()

    def copy_rows(self, *_):
        idx = sorted(int(i) for i in self.tree.selection())
        if idx:
            buf = io.StringIO()
            csv.writer(buf, delimiter="\t", lineterminator="\n").writerows(self.rows[i] for i in idx)
            self.clipboard_clear()
            self.clipboard_append(buf.getvalue())
            self.log("view", "copy", f"{len(idx):,} row(s) \u2192 clipboard (TSV)")
        return "break"

    # ------------------------------------------------------- inline editing -- #
    def on_double_click(self, e):
        if self.tree.identify_region(e.x, e.y) != "cell":
            return
        iid = self.tree.identify_row(e.y)
        ci = int(self.tree.identify_column(e.x)[1:]) - 1
        if iid and 0 <= ci < len(self.cols):
            self.begin_edit(iid, ci)

    def begin_edit(self, iid, ci):
        self.end_edit(True)
        if not self.tree.exists(iid):
            return
        box = self.tree.bbox(iid, f"c{ci}")
        if not box:
            return
        x, y, w, h = box
        ri = int(iid)
        ent = tk.Entry(self.tree, bg=PANEL, fg=ACCENT, insertbackground=ACCENT, relief="flat",
                       font=self.f, highlightthickness=1, highlightbackground=ACCENT,
                       highlightcolor=ACCENT)
        ent.insert(0, self.rows[ri][ci])
        ent.select_range(0, "end")
        ent.place(x=x, y=y, width=w, height=h)
        ent.focus_set()
        ent.bind("<Return>", lambda e: self.end_edit(True))
        ent.bind("<Escape>", lambda e: self.end_edit(False))
        ent.bind("<FocusOut>", lambda e: self.end_edit(True))
        self._edit = (ent, ri, ci)

    def end_edit(self, commit):
        if not self._edit:
            return
        ent, ri, ci = self._edit
        self._edit = None
        new = ent.get()
        ent.destroy()
        if not commit or ri >= len(self.rows) or new == self.rows[ri][ci]:
            return
        old = self.rows[ri][ci]

        def op():
            self.rows[ri][ci] = new
            return (f"row {ri + 1} \u00b7 {self.cols[ci]}: {clip(old, 20)} \u2192 {clip(new, 20)}", 1)
        self.run("EDIT CELL", op, keep=(ri,))

    # ------------------------------------------------------------ side panel #
    def schedule_panel(self):
        if self._after_panel is None:
            self._after_panel = self.after_idle(self.refresh_panel)

    def refresh_panel(self):
        self._after_panel = None
        n, m = len(self.rows), len(self.cols)
        if self._stats[0] != self.rev:        # O(n): only when the data actually changed
            empty = sum(1 for r in self.rows for c in r if is_null(c))
            self._stats = (self.rev, empty, n - len({tuple(r) for r in self.rows}))
        _, empty, dups = self._stats
        name = os.path.basename(self.path) if self.path else ("untitled" if self.cols else "\u2014")
        q = self.filter_var.get().strip()
        self.kv["file"].set(trunc(name, 26))
        self.kv["rows"].set(f"{n:,}" + (f"  \u00b7  {self.match_count:,} match" if q else ""))
        self.kv["columns"].set(str(m))
        self.kv["empty cells"].set(f"{empty:,}" + (f"  ({empty / (n * m) * 100:.1f}%)" if n * m else ""))
        self.kv["duplicates"].set(f"{dups:,}")
        self.kv["state"].set("\u2014" if not self.cols else ("modified" if self.dirty else "saved"))
        self.kv["history"].set(f"undo {len(self.undo_stack)}  \u00b7  redo {len(self.redo_stack)}")
        self.btn_undo.set_enabled(bool(self.undo_stack))
        self.btn_redo.set_enabled(bool(self.redo_stack))

        key = (self.rev, self.active, m)
        if self._prof_key != key:
            self._prof_key, self._prof_val = key, self.profile()
        title, lines = self._prof_val
        self.col_title.configure(text=trunc(title, 40))
        p = self.prof
        p.configure(state="normal")
        p.delete("1.0", "end")
        for k, v in lines:
            p.insert("end", f"{k:<9}", "k")
            p.insert("end", v + "\n")
        p.configure(state="disabled")

    def profile(self):
        if not self.cols:
            return "\u2014", []
        ci = max(0, min(self.active, len(self.cols) - 1))
        vals = [r[ci] for r in self.rows]
        filled = [v for v in vals if not is_null(v)]
        nums = [to_num(v) for v in filled]
        numeric = bool(filled) and None not in nums
        if not filled:
            kind = "empty"
        elif numeric:
            kind = "integer" if all(_INT.match(v.strip()) for v in filled) else "float"
        else:
            kind = "text"
        n = len(vals)
        out = [("type", kind),
               ("filled", f"{len(filled):,}" + (f"  ({len(filled) / n * 100:.1f}%)" if n else "")),
               ("missing", f"{n - len(filled):,}"),
               ("unique", f"{len(set(filled)):,}")]
        if numeric:
            out += [("min", fmt_num(min(nums))), ("max", fmt_num(max(nums))),
                    ("mean", fmt_num(statistics.fmean(nums))),
                    ("median", fmt_num(statistics.median(nums)))]
            if len(nums) > 1:
                out.append(("stdev", fmt_num(statistics.stdev(nums))))
        elif filled:
            lens = [len(v) for v in filled]
            out.append(("length", f"{min(lens)}\u2013{max(lens)}"))
            for i, (v, c) in enumerate(Counter(filled).most_common(3)):
                out.append(("top" if i == 0 else "", f"{clip(v, 16)} \u00d7{c:,}"))
        return self.cols[ci], out

    # ------------------------------------------------------ helpers for ops -- #
    def col_field(self, allow_all=False, label="Column"):
        opts = ([ALL] if allow_all else []) + self.cols
        default = ALL if allow_all else self.cols[max(0, min(self.active, len(self.cols) - 1))]
        return dict(key="col", label=label, kind="choice", options=opts, default=default)

    def targets(self, name):
        return list(range(len(self.cols))) if name == ALL else [self.cols.index(name)]

    @staticmethod
    def scope(name):
        return "all columns" if name == ALL else f'"{name}"'

    # ---------------------------------------------------------- row ops ----- #
    def op_add_row(self):
        sel = sorted(int(i) for i in self.tree.selection())
        pos = sel[-1] + 1 if sel else len(self.rows)
        if self.filter_var.get().strip():
            self.clear_filter()

        def op():
            self.rows.insert(pos, [""] * len(self.cols))
            return (f"inserted at row {pos + 1}", 1)
        if self.run("ADD ROW", op):
            iid = str(pos)
            if self.tree.exists(iid):
                self.tree.selection_set(iid)
                self.tree.see(iid)

    def op_delete_rows(self):
        idx = sorted({int(i) for i in self.tree.selection()})
        if not idx:
            self.log("warn", "delete rows", "Select one or more rows first.")
            return
        self._delete_indices("DELETE ROWS", idx)

    def op_delete_matching(self):
        if not self.filter_var.get().strip():
            self.log("warn", "delete matching", "Type a filter first.")
            return
        idx = self.visible_indices()
        if not idx:
            self.log("warn", "delete matching", "No rows match the filter.")
            return
        if not messagebox.askyesno(APP, f"Delete {len(idx):,} rows matching the filter?"):
            return
        self.clear_filter()
        if not self._delete_indices("DELETE MATCHING", idx):
            self.render()                    # the filter is cleared; show all rows again

    def _delete_indices(self, name, idx) -> bool:
        def op():
            drop = set(idx)
            self.rows[:] = [r for i, r in enumerate(self.rows) if i not in drop]
            return (f"removed {len(idx):,} row(s) \u00b7 first was #{idx[0] + 1}", len(idx))
        return self.run(name, op)

    def op_sort(self):
        f = self.ask("Sort", [self.col_field(),
                              dict(key="order", label="Order", kind="choice",
                                   options=["Ascending", "Descending"]),
                              dict(key="mode", label="Compare as", kind="choice",
                                   options=["Auto", "Numeric", "Text"])], ok="Sort")
        if f:
            self.do_sort(self.cols.index(f["col"]), f["order"] == "Ascending", f["mode"].lower())

    def do_sort(self, ci, asc, mode):
        flipped_only = False

        def op():
            nonlocal flipped_only
            filled = [r for r in self.rows if not is_null(r[ci])]
            empty = [r for r in self.rows if is_null(r[ci])]
            nums = [to_num(r[ci]) for r in filled]
            numeric = bool(filled) and None not in nums
            if mode == "numeric" and not numeric:
                bad = sum(1 for n in nums if n is None)
                raise OpError(f"{bad:,} non-numeric value(s) in this column")
            use_num = numeric and mode in ("auto", "numeric")
            keys = nums if use_num else [r[ci].casefold() for r in filled]
            order = sorted(range(len(filled)), key=keys.__getitem__, reverse=not asc)
            new = [filled[k] for k in order] + empty
            moved = sum(1 for a, b in zip(self.rows, new) if a is not b)
            if not moved:
                self.sort_state, flipped_only = (ci, asc), True   # next click will flip
                return ("already in this order", 0)
            self.rows[:] = new
            self.sort_state = (ci, asc)
            return (f'"{self.cols[ci]}" {"ascending" if asc else "descending"} \u00b7 '
                    f'{"numeric" if use_num else "text"} \u00b7 empty values last \u00b7 '
                    f"{moved:,} rows moved", moved)
        self.run("SORT", op)
        if flipped_only:
            self.render()                    # refresh the header arrow

    def op_dedupe(self):
        f = self.ask("Drop duplicates", [
            self.col_field(allow_all=True, label="Compare on"),
            dict(key="keep", label="Keep", kind="choice", options=["first", "last"])])
        if not f:
            return

        def op():
            idx = self.targets(f["col"])
            seq = self.rows if f["keep"] == "first" else self.rows[::-1]
            seen, kept = set(), []
            for r in seq:
                k = tuple(r[i] for i in idx)
                if k not in seen:
                    seen.add(k)
                    kept.append(r)
            if f["keep"] == "last":
                kept.reverse()
            removed = len(self.rows) - len(kept)
            if not removed:
                return ("no duplicates found (exact match)", 0)
            self.rows[:] = kept
            return (f"removed {removed:,} duplicate row(s) \u00b7 compared on "
                    f"{self.scope(f['col'])} \u00b7 kept {f['keep']}", removed)
        self.run("DROP DUPLICATES", op)

    def op_drop_empty(self):
        def op():
            kept = [r for r in self.rows if not all(is_null(c) for c in r)]
            removed = len(self.rows) - len(kept)
            if not removed:
                return ("no empty rows", 0)
            self.rows[:] = kept
            return (f"removed {removed:,} row(s) where every cell is empty", removed)
        self.run("DROP EMPTY ROWS", op)

    # ------------------------------------------------------- column ops ----- #
    def op_add_col(self):
        f = self.ask("Add column", [
            dict(key="name", label="Name"),
            dict(key="value", label="Default value"),
            dict(key="pos", label="Position", kind="choice",
                 options=["At end", "After active column"])])
        if not f:
            return
        name = f["name"].strip()

        def op():
            if not name:
                raise OpError("column name is empty")
            if name.casefold() in {c.casefold() for c in self.cols}:
                raise OpError(f'column "{name}" already exists')
            at = self.active + 1 if f["pos"].startswith("After") else len(self.cols)
            self.cols.insert(at, name)
            for r in self.rows:
                r.insert(at, f["value"])
            extra = f" \u00b7 default {clip(f['value'])}" if f["value"] else ""
            return (f'"{name}" at position {at + 1}{extra}', max(len(self.rows), 1))
        self.run("ADD COLUMN", op)

    def op_rename_col(self):
        f = self.ask("Rename column", [self.col_field(), dict(key="name", label="New name")])
        if not f:
            return

        def op():
            old, new = f["col"], f["name"].strip()
            if not new:
                raise OpError("new name is empty")
            if new == old:
                return ("name unchanged", 0)
            if new.casefold() in {c.casefold() for c in self.cols if c != old}:
                raise OpError(f'column "{new}" already exists')
            self.cols[self.cols.index(old)] = new
            return (f'"{old}" \u2192 "{new}"', 1)
        self.run("RENAME COLUMN", op)

    def op_delete_col(self):
        f = self.ask("Delete column", [self.col_field()], ok="Delete")
        if not f:
            return

        def op():
            if len(self.cols) < 2:
                raise OpError("a dataset needs at least one column")
            ci = self.cols.index(f["col"])
            del self.cols[ci]
            for r in self.rows:
                del r[ci]
            return (f'removed "{f["col"]}"', max(len(self.rows), 1))
        self.run("DELETE COLUMN", op)

    # --------------------------------------------------------- clean ops ---- #
    def op_trim(self):
        f = self.ask("Trim whitespace", [
            self.col_field(allow_all=True),
            dict(key="inner", label="Also collapse repeated inner whitespace",
                 kind="check", default=True)])
        if not f:
            return

        def op():
            idx, n = self.targets(f["col"]), 0
            for r in self.rows:
                for ci in idx:
                    v = r[ci]
                    nv = " ".join(v.split()) if f["inner"] else v.strip()
                    if nv != v:
                        r[ci], n = nv, n + 1
            return (f"{n:,} cell(s) changed \u00b7 {self.scope(f['col'])}", n)
        self.run("TRIM", op)

    def op_fill(self):
        f = self.ask("Fill missing values", [
            self.col_field(),
            dict(key="method", label="Method", kind="choice",
                 options=["constant", "mean", "median", "mode"]),
            dict(key="value", label="Constant value (for 'constant')")])
        if not f:
            return

        def op():
            ci, method = self.cols.index(f["col"]), f["method"]
            missing = [r for r in self.rows if is_null(r[ci])]
            if not missing:
                return (f'no missing values in "{f["col"]}"', 0)
            filled = [r[ci] for r in self.rows if not is_null(r[ci])]
            if method == "constant":
                if f["value"] == "":
                    raise OpError("constant value is empty")
                fill = f["value"]
            elif method == "mode":
                if not filled:
                    raise OpError("column has no values to take a mode from")
                fill = Counter(filled).most_common(1)[0][0]
            else:
                nums = [to_num(v) for v in filled]
                if not nums or None in nums:
                    raise OpError(f"{method} needs a fully numeric column")
                fill = fmt_num(statistics.fmean(nums) if method == "mean" else statistics.median(nums))
            for r in missing:
                r[ci] = fill
            return (f'{len(missing):,} cell(s) in "{f["col"]}" \u2190 {clip(fill)} ({method})',
                    len(missing))
        self.run("FILL MISSING", op)

    def op_case(self):
        f = self.ask("Change case", [
            self.col_field(allow_all=True),
            dict(key="mode", label="Convert to", kind="choice", options=["lower", "UPPER", "Title"])])
        if not f:
            return
        fn = {"lower": str.lower, "UPPER": str.upper, "Title": title_case}[f["mode"]]

        def op():
            idx, n = self.targets(f["col"]), 0
            for r in self.rows:
                for ci in idx:
                    nv = fn(r[ci])
                    if nv != r[ci]:
                        r[ci], n = nv, n + 1
            return (f"{n:,} cell(s) \u2192 {f['mode']} \u00b7 {self.scope(f['col'])}", n)
        self.run("CHANGE CASE", op)

    def op_replace(self):
        f = self.ask("Find & replace", [
            self.col_field(allow_all=True),
            dict(key="find", label="Find"),
            dict(key="repl", label="Replace with"),
            dict(key="regex", label="Regular expression", kind="check"),
            dict(key="case", label="Match case", kind="check")])
        if not f:
            return

        def op():
            if f["find"] == "":
                raise OpError("'find' is empty")
            flags = 0 if f["case"] else re.IGNORECASE
            try:
                pat = re.compile(f["find"] if f["regex"] else re.escape(f["find"]), flags)
            except re.error as e:
                raise OpError(f"invalid pattern: {e}")
            repl = f["repl"] if f["regex"] else (lambda m: f["repl"])
            idx, cells, subs = self.targets(f["col"]), 0, 0
            try:
                for r in self.rows:
                    for ci in idx:
                        nv, k = pat.subn(repl, r[ci])
                        if k and nv != r[ci]:
                            r[ci], cells, subs = nv, cells + 1, subs + k
            except (re.error, IndexError) as e:
                raise OpError(f"invalid replacement: {e}")
            return (f"{subs:,} replacement(s) in {cells:,} cell(s) \u00b7 {clip(f['find'], 16)} "
                    f"\u2192 {clip(f['repl'], 16)} \u00b7 {self.scope(f['col'])}", cells)
        self.run("FIND & REPLACE", op)


def main():
    try:
        from ctypes import windll  # crisp text on Windows high-DPI displays
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:  # noqa: BLE001
        pass
    App(sys.argv[1] if len(sys.argv) > 1 else None).mainloop()


if __name__ == "__main__":
    main()
