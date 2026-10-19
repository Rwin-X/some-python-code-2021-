"""
T-CI LAB · TWO SAMPLES — confidence interval for the difference of two means (μ₂ − μ₁)

Formula from the book (known common variance σ²):

    (ȳ − x̄) − z(α/2)·√(σ²/m + σ²/n)  <  μ₂ − μ₁  <  (ȳ − x̄) + z(α/2)·√(σ²/m + σ²/n)

    X₁..Xₙ ~ N(μ₁, σ²)   → sample X: size n, mean x̄
    Y₁..Yₘ ~ N(μ₂, σ²)   → sample Y: size m, mean ȳ

Extra methods:  z with different known σ₁, σ₂   ·   pooled t (σ unknown but equal)

Requirements:  pip install scipy        (tkinter ships with Python)
Run:           python ci_lab_two_sample.py

BY RWIN ANDISHE
"""

import csv
import math
import re
import statistics
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, font as tkfont, ttk

from scipy import stats

# ───────────────────────────── THEME ─────────────────────────────
BG = "#080c09"
PANEL = "#0d130f"
PANEL2 = "#121a14"
BORDER = "#1d2a21"
FG = "#d3e0d6"
DIM = "#6f8274"
GREEN = "#39ff88"
GREEN_DK = "#14452a"
CYAN = "#3fd8ff"
RED = "#ff5c6c"
AMBER = "#ffc857"
TAIL = "#4a1e26"

LEVELS = [0.80, 0.90, 0.95, 0.99, 0.999]
SIDE_NAMES = {
    "two": "Two-sided",
    "lower": "Lower confidence bound",
    "upper": "Upper confidence bound",
}
METHOD_NAMES = {
    "z": "z · common known σ  (book formula)",
    "z2": "z · known σ₁, σ₂",
    "t": "pooled t · σ unknown but equal",
}
FORMULAS = {
    "z": "(ȳ − x̄) ± z·√(σ²/m + σ²/n)",
    "z2": "(ȳ − x̄) ± z·√(σ₁²/n + σ₂²/m)",
    "t": "(ȳ − x̄) ± t·sₚ·√(1/n + 1/m)",
}


# ───────────────────────── PARSING HELPERS ─────────────────────────
class Waiting(Exception):
    """Inputs are incomplete (not an error, just not ready)."""


class InputError(Exception):
    """Inputs are present but invalid."""


_MAP = {}
for _i, (_p, _a) in enumerate(zip("۰۱۲۳۴۵۶۷۸۹", "٠١٢٣٤٥٦٧٨٩")):
    _MAP[ord(_p)] = str(_i)
    _MAP[ord(_a)] = str(_i)
_MAP[ord("٫")] = "."
_MAP[ord("٬")] = None
_MAP[ord("−")] = "-"


def norm(text):
    """Persian/Arabic digits → ASCII, strip spaces."""
    return text.translate(_MAP).strip()


def to_float(text, name):
    try:
        v = float(norm(text))
    except ValueError:
        raise InputError(f"{name} is not a number")
    if not math.isfinite(v):
        raise InputError(f"{name} must be a finite number")
    return v


def to_int(text, name):
    try:
        return int(norm(text))
    except ValueError:
        raise InputError(f"{name} must be a whole number")


def parse_confidence(text):
    v = float(norm(text).replace("%", "").strip())
    if v > 1:
        v /= 100
    return v


def parse_data(text):
    tokens = [t for t in re.split(r"[\s,;،]+", norm(text)) if t]
    values = []
    for tok in tokens:
        try:
            v = float(tok)
        except ValueError:
            raise ValueError(f"'{tok}' is not a number")
        if not math.isfinite(v):
            raise ValueError(f"'{tok}' is not a finite number")
        values.append(v)
    return values


# ───────────────────────────── CORE MATH ─────────────────────────────
def compute(n, xbar, m, ybar, conf, side="two", method="z",
            sigma=None, sigma1=None, sigma2=None, sx=None, sy=None):
    """Confidence interval for μ₂ − μ₁."""
    alpha = 1 - conf
    q = 1 - alpha / 2 if side == "two" else 1 - alpha
    diff = ybar - xbar                                  # point estimate ȳ − x̄
    df = None
    sp = None

    if method == "z":                                   # σ²/m + σ²/n
        se = math.sqrt(sigma ** 2 / m + sigma ** 2 / n)
        crit = float(stats.norm.ppf(q))
    elif method == "z2":                                # σ₁²/n + σ₂²/m
        se = math.sqrt(sigma1 ** 2 / n + sigma2 ** 2 / m)
        crit = float(stats.norm.ppf(q))
    else:                                               # pooled t
        df = n + m - 2                                  # DARAGE AZADI
        sp = math.sqrt(((n - 1) * sx ** 2 + (m - 1) * sy ** 2) / df)
        se = sp * math.sqrt(1 / n + 1 / m)
        crit = float(stats.t.ppf(q, df))

    me = crit * se                                      # margin of error
    lower = diff - me if side in ("two", "lower") else -math.inf   # KAMTARIN
    upper = diff + me if side in ("two", "upper") else math.inf    # BISHTARIN

    return {
        "inp": dict(n=n, xbar=xbar, m=m, ybar=ybar, conf=conf, side=side, method=method,
                    sigma=sigma, sigma1=sigma1, sigma2=sigma2, sx=sx, sy=sy),
        "n": n, "xbar": xbar, "m": m, "ybar": ybar, "conf": conf, "alpha": alpha,
        "side": side, "method": method, "sigma": sigma, "sigma1": sigma1,
        "sigma2": sigma2, "sx": sx, "sy": sy, "df": df, "sp": sp, "diff": diff,
        "crit": crit, "se": se, "me": me, "lower": lower, "upper": upper,
    }


def fmt(x, d):
    if x == math.inf:
        return "∞"
    if x == -math.inf:
        return "−∞"
    return f"{x:.{d}f}"


def ci_string(r, d):
    return f"({fmt(r['lower'], d)}, {fmt(r['upper'], d)})"


def caption(r):
    c = f"{r['conf'] * 100:g}%"
    return {
        "two": f"{c} CONFIDENCE INTERVAL FOR  μ₂ − μ₁",
        "lower": f"{c} LOWER CONFIDENCE BOUND FOR  μ₂ − μ₁",
        "upper": f"{c} UPPER CONFIDENCE BOUND FOR  μ₂ − μ₁",
    }[r["side"]]


def interpretation(r, d):
    c = f"{r['conf'] * 100:g}%"
    lo, up = fmt(r["lower"], d), fmt(r["upper"], d)
    if r["side"] == "two":
        text = (f"We are {c} confident that the true difference μ₂ − μ₁ lies between "
                f"{lo} and {up}.\n")
        if r["lower"] > 0:
            text += "The whole interval is above 0 → μ₂ is larger than μ₁ (significant at this level)."
        elif r["upper"] < 0:
            text += "The whole interval is below 0 → μ₂ is smaller than μ₁ (significant at this level)."
        else:
            text += "The interval contains 0 → no significant difference between μ₁ and μ₂ at this level."
        return text
    if r["side"] == "lower":
        text = f"We are {c} confident that μ₂ − μ₁ is at least {lo}."
        if r["lower"] > 0:
            text += "\nThe bound is above 0 → μ₂ > μ₁."
        return text
    text = f"We are {c} confident that μ₂ − μ₁ is at most {up}."
    if r["upper"] < 0:
        text += "\nThe bound is below 0 → μ₂ < μ₁."
    return text


def report_text(r, d):
    sym = "t" if r["method"] == "t" else "z"
    lines = [
        "T-CI LAB · TWO SAMPLES — Confidence Interval for μ2 − μ1",
        "=" * 56,
        f"Method              : {METHOD_NAMES[r['method']]}",
        f"Formula             : {FORMULAS[r['method']]}",
        f"Interval type       : {SIDE_NAMES[r['side']]}",
        f"Sample X  (n)       : {r['n']}",
        f"Sample mean x-bar   : {r['xbar']}",
        f"Sample Y  (m)       : {r['m']}",
        f"Sample mean y-bar   : {r['ybar']}",
    ]
    if r["method"] == "z":
        lines.append(f"Common sigma        : {r['sigma']}")
    elif r["method"] == "z2":
        lines.append(f"sigma1 / sigma2     : {r['sigma1']} / {r['sigma2']}")
    else:
        lines.append(f"sx / sy             : {r['sx']} / {r['sy']}")
        lines.append(f"Pooled sp           : {r['sp']:.{d}f}")
        lines.append(f"Degrees of freedom  : {r['df']}")
    lines += [
        f"Confidence level    : {r['conf'] * 100:g}%",
        f"{sym}-critical value    : {r['crit']:.4f}",
        f"Estimate (y-x)      : {r['diff']:.{d}f}",
        f"Standard error      : {r['se']:.{d}f}",
        f"Margin of error     : {r['me']:.{d}f}",
        f"Lower bound         : {fmt(r['lower'], d)}",
        f"Upper bound         : {fmt(r['upper'], d)}",
        "",
        f"{caption(r).title()}: {ci_string(r, d)}",
        "",
        interpretation(r, d),
    ]
    return "\n".join(lines)


def pick_family():
    available = set(tkfont.families())
    for name in ("JetBrains Mono", "Cascadia Mono", "Consolas", "Menlo",
                 "DejaVu Sans Mono", "Courier New"):
        if name in available:
            return name
    return "Courier"


# ───────────────────────────── APPLICATION ─────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("T-CI LAB · Two Samples — μ₂ − μ₁")
        self.configure(bg=BG)
        self.geometry("1240x920")
        self.minsize(1080, 800)

        self.family = pick_family()
        self.last = None
        self.history = []
        self._job = None
        self.row_defs = []     # (widgets, methods) → show/hide rows by method

        self._init_vars()
        self._init_style()
        self._build()
        self._wire()
        self.update_rows()
        self.schedule()

    def F(self, size=10, bold=False):
        return (self.family, size, "bold" if bold else "normal")

    # ───────────── variables / style ─────────────
    def _init_vars(self):
        self.v_n = tk.StringVar()
        self.v_xbar = tk.StringVar()
        self.v_sx = tk.StringVar()
        self.v_m = tk.StringVar()
        self.v_ybar = tk.StringVar()
        self.v_sy = tk.StringVar()
        self.v_sigma = tk.StringVar()
        self.v_s1 = tk.StringVar()
        self.v_s2 = tk.StringVar()
        self.v_conf = tk.StringVar(value="95")
        self.v_side = tk.StringVar(value="two")
        self.v_method = tk.StringVar(value="z")
        self.v_mode = tk.StringVar(value="summary")
        self.v_dec = tk.IntVar(value=4)

    def _init_style(self):
        st = ttk.Style(self)
        st.theme_use("clam")
        st.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        st.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=FG,
                     rowheight=24, borderwidth=0, font=self.F(10))
        st.configure("Treeview.Heading", background=PANEL2, foreground=DIM, relief="flat",
                     borderwidth=0, font=self.F(9, True))
        st.map("Treeview", background=[("selected", GREEN_DK)],
               foreground=[("selected", GREEN)])
        st.map("Treeview.Heading", background=[("active", PANEL2)])
        st.configure("TNotebook", background=BG, borderwidth=0, tabmargins=0,
                     bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
        st.configure("TNotebook.Tab", background=PANEL, foreground=DIM, padding=(16, 6),
                     borderwidth=0, font=self.F(9, True), bordercolor=BORDER,
                     lightcolor=PANEL, darkcolor=PANEL, focuscolor=PANEL)
        st.map("TNotebook.Tab", background=[("selected", PANEL2)],
               foreground=[("selected", GREEN)])
        st.configure("Vertical.TScrollbar", background=PANEL2, troughcolor=PANEL,
                     bordercolor=PANEL, arrowcolor=DIM, lightcolor=PANEL2, darkcolor=PANEL2)

    # ───────────── widget factories ─────────────
    def card(self, parent, title):
        outer = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        tk.Label(outer, text=title, bg=PANEL, fg=CYAN, font=self.F(9, True),
                 anchor="w").pack(fill="x", padx=12, pady=(8, 2))
        inner = tk.Frame(outer, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=12, pady=(2, 10))
        return outer, inner

    def label(self, parent, text, color=FG, size=10, bold=False, **kw):
        return tk.Label(parent, text=text, bg=kw.pop("bg", PANEL), fg=color,
                        font=self.F(size, bold), **kw)

    def entry(self, parent, var, width=14):
        e = tk.Entry(parent, textvariable=var, width=width, bg=BG, fg=GREEN,
                     insertbackground=GREEN, relief="flat", font=self.F(11),
                     highlightthickness=1, highlightbackground=BORDER, highlightcolor=GREEN,
                     disabledbackground=PANEL, disabledforeground=DIM)
        e.bind("<Return>", lambda ev: self.calculate(record=True))
        return e

    def button(self, parent, text, cmd, color=GREEN, filled=False, small=False):
        bg, fg = (color, BG) if filled else (PANEL, color)
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, activebackground=color,
                      activeforeground=BG, relief="flat", bd=0,
                      font=self.F(9 if small else 10, True),
                      padx=10 if small else 16, pady=3 if small else 7, cursor="hand2",
                      highlightthickness=1, highlightbackground=color)
        if not filled:
            b.bind("<Enter>", lambda e: b.config(bg=color, fg=BG))
            b.bind("<Leave>", lambda e: b.config(bg=bg, fg=fg))
        return b

    def segmented(self, parent, var, options, command=None):
        frame = tk.Frame(parent, bg=BORDER)
        buttons = []

        def refresh(*_):
            for value, rb in buttons:
                rb.config(fg=GREEN if var.get() == value else DIM)

        for i, (value, text) in enumerate(options):
            rb = tk.Radiobutton(frame, text=text, value=value, variable=var, indicatoron=0,
                                bg=PANEL2, fg=DIM, selectcolor=GREEN_DK,
                                activebackground=GREEN_DK, activeforeground=GREEN,
                                relief="flat", bd=0, font=self.F(9, True), padx=6, pady=6,
                                cursor="hand2", highlightthickness=0, command=command)
            rb.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 1, 0))
            frame.grid_columnconfigure(i, weight=1, uniform="seg")
            buttons.append((value, rb))
        var.trace_add("write", refresh)
        refresh()
        return frame

    def add_header(self, frame, row, text, color):
        lbl = self.label(frame, text, color, 9, True)
        lbl.grid(row=row, column=0, columnspan=2, sticky="w", pady=(6, 0))
        return lbl

    def add_row(self, frame, row, text, var, methods=None, width=12):
        lbl = self.label(frame, text, FG, 10)
        lbl.grid(row=row, column=0, sticky="w", pady=3)
        ent = self.entry(frame, var, width)
        ent.grid(row=row, column=1, sticky="e", padx=(10, 0), ipady=2)
        self.row_defs.append(([lbl, ent], methods))
        return ent

    # ───────────── layout ─────────────
    def _build(self):
        root = tk.Frame(self, bg=BG)
        root.pack(fill="both", expand=True)

        hdr = tk.Frame(root, bg=BG)
        hdr.pack(fill="x", padx=18, pady=(14, 8))
        tk.Label(hdr, text="▌T-CI LAB", bg=BG, fg=GREEN, font=self.F(18, True)).pack(side="left")
        tk.Label(hdr, text="   two samples · confidence interval for  μ₂ − μ₁",
                 bg=BG, fg=DIM, font=self.F(10)).pack(side="left", pady=(8, 0))
        tk.Label(hdr, text="BY RWIN ANDISHE", bg=BG, fg=DIM, font=self.F(9)).pack(side="right")
        tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=18)

        foot = tk.Label(root, anchor="w", bg=BG, fg=DIM, font=self.F(8),
                        text="Enter = calculate & save to history   ·   Ctrl+L = clear   ·   "
                             "Ctrl+Shift+C = copy report   ·   results update live while you type")
        foot.pack(side="bottom", fill="x", padx=18, pady=(0, 8))

        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True, padx=18, pady=12)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 14))
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")

        self._build_left(left)
        self._build_right(right)

    def _build_left(self, left):
        # ── SAMPLES ──
        box, inner = self.card(left, "// SAMPLES")
        box.pack(fill="x", pady=(0, 10))
        self.segmented(inner, self.v_mode,
                       [("summary", "SUMMARY STATS"), ("raw", "RAW DATA")],
                       command=self.switch_mode).pack(fill="x", pady=(0, 6))

        self.in_box = tk.Frame(inner, bg=PANEL)
        self.in_box.pack(fill="x")

        # summary: X then Y
        self.sum_frame = tk.Frame(self.in_box, bg=PANEL)
        self.sum_frame.grid_columnconfigure(1, weight=1)
        self.add_header(self.sum_frame, 0, "SAMPLE X  →  μ₁", CYAN)
        self.n_entry = self.add_row(self.sum_frame, 1, "n  · size", self.v_n)
        self.add_row(self.sum_frame, 2, "x̄  · mean", self.v_xbar)
        self.add_row(self.sum_frame, 3, "sₓ · std dev", self.v_sx, {"t"})
        self.add_header(self.sum_frame, 4, "SAMPLE Y  →  μ₂", AMBER)
        self.add_row(self.sum_frame, 5, "m  · size", self.v_m)
        self.add_row(self.sum_frame, 6, "ȳ  · mean", self.v_ybar)
        self.add_row(self.sum_frame, 7, "s_y · std dev", self.v_sy, {"t"})
        self.sum_frame.pack(fill="x")

        # raw: two text boxes
        self.raw_frame = tk.Frame(self.in_box, bg=PANEL)
        self.raw_x, self.info_x = self._raw_block("SAMPLE X  →  μ₁", CYAN)
        self.raw_y, self.info_y = self._raw_block("SAMPLE Y  →  μ₂", AMBER)
        self.label(self.raw_frame, "numbers separated by space, comma or newline",
                   DIM, 8).pack(anchor="w", pady=(4, 0))

        self.button(inner, "LOAD EXAMPLE", self.load_example, DIM, small=True).pack(
            anchor="w", pady=(8, 0))

        # ── PARAMETERS ──
        box2, inner2 = self.card(left, "// PARAMETERS")
        box2.pack(fill="x", pady=(0, 10))

        self.label(inner2, "confidence level", DIM, 9).pack(anchor="w")
        crow = tk.Frame(inner2, bg=PANEL)
        crow.pack(fill="x", pady=(3, 8))
        self.conf_entry = self.entry(crow, self.v_conf, 7)
        self.conf_entry.pack(side="left", ipady=2)
        self.label(crow, "%", DIM, 11).pack(side="left", padx=(3, 8))
        for txt in ("90", "95", "99", "99.9"):
            self.button(crow, txt, lambda t=txt: self.v_conf.set(t), CYAN, small=True).pack(
                side="left", padx=(0, 4))

        self.label(inner2, "interval type", DIM, 9).pack(anchor="w")
        self.segmented(inner2, self.v_side,
                       [("two", "TWO-SIDED"), ("lower", "LOWER"), ("upper", "UPPER")]).pack(
            fill="x", pady=(3, 8))

        self.label(inner2, "method", DIM, 9).pack(anchor="w")
        self.segmented(inner2, self.v_method,
                       [("z", "z · σ"), ("z2", "z · σ₁,σ₂"), ("t", "t · pooled")]).pack(
            fill="x", pady=(3, 4))

        # known σ rows (shown only for z methods)
        self.sig_frame = tk.Frame(inner2, bg=PANEL)
        self.sig_frame.pack(fill="x")
        self.sig_frame.grid_columnconfigure(1, weight=1)
        self.add_row(self.sig_frame, 0, "σ   · common (known)", self.v_sigma, {"z"}, 10)
        self.add_row(self.sig_frame, 1, "σ₁  · of X (known)", self.v_s1, {"z2"}, 10)
        self.add_row(self.sig_frame, 2, "σ₂  · of Y (known)", self.v_s2, {"z2"}, 10)

        drow = tk.Frame(inner2, bg=PANEL)
        drow.pack(fill="x", pady=(8, 0))
        self.label(drow, "decimal places", FG, 10).pack(side="left")
        tk.Spinbox(drow, from_=0, to=10, width=4, textvariable=self.v_dec, bg=BG, fg=GREEN,
                   insertbackground=GREEN, buttonbackground=PANEL2, relief="flat",
                   font=self.F(11), highlightthickness=1, highlightbackground=BORDER,
                   highlightcolor=GREEN, justify="center").pack(side="right")

        # ── ACTIONS ──
        arow = tk.Frame(left, bg=BG)
        arow.pack(fill="x")
        self.button(arow, "CALCULATE", lambda: self.calculate(record=True), GREEN,
                    filled=True).pack(side="left")
        self.button(arow, "CLEAR", self.clear, DIM).pack(side="left", padx=8)

        self.status = tk.Label(left, text="", bg=BG, fg=DIM, font=self.F(9), anchor="w",
                               justify="left", wraplength=340)
        self.status.pack(fill="x", pady=(10, 0))

    def _raw_block(self, title, color):
        self.label(self.raw_frame, title, color, 9, True).pack(anchor="w", pady=(6, 2))
        txt = tk.Text(self.raw_frame, width=34, height=4, bg=BG, fg=GREEN,
                      insertbackground=GREEN, relief="flat", font=self.F(10),
                      highlightthickness=1, highlightbackground=BORDER,
                      highlightcolor=GREEN, wrap="word", undo=True)
        txt.pack(fill="x")
        info = self.label(self.raw_frame, "", color, 8, True)
        info.pack(anchor="w", pady=(2, 0))
        return txt, info

    def _build_right(self, right):
        # ── RESULT ──
        rbox, rin = self.card(right, "// RESULT")
        rbox.pack(fill="x", pady=(0, 10))
        top = tk.Frame(rin, bg=PANEL)
        top.pack(fill="x")
        self.ci_caption = self.label(top, "CONFIDENCE INTERVAL FOR  μ₂ − μ₁", DIM, 9)
        self.ci_caption.pack(side="left")
        self.formula_lbl = self.label(top, FORMULAS["z"], CYAN, 9)
        self.formula_lbl.pack(side="right")
        self.ci_big = self.label(rin, "—", DIM, 26, True)
        self.ci_big.pack(anchor="w", pady=(0, 8))

        tiles = tk.Frame(rin, bg=PANEL)
        tiles.pack(fill="x")
        self.tiles = {}
        for i, key in enumerate(("crit", "diff", "se", "me", "extra")):
            t = tk.Frame(tiles, bg=PANEL2, highlightbackground=BORDER, highlightthickness=1)
            t.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0))
            tiles.grid_columnconfigure(i, weight=1, uniform="tile")
            cap = self.label(t, key, DIM, 8, bg=PANEL2)
            cap.pack(anchor="w", padx=8, pady=(6, 0))
            val = self.label(t, "—", FG, 13, True, bg=PANEL2)
            val.pack(anchor="w", padx=8, pady=(0, 6))
            self.tiles[key] = (cap, val)

        self.interp = self.label(rin, "", FG, 10, justify="left", anchor="w")
        self.interp.pack(fill="x", pady=(10, 0))
        rbox.bind("<Configure>", lambda e: self.interp.config(wraplength=max(200, e.width - 50)))

        brow = tk.Frame(rin, bg=PANEL)
        brow.pack(fill="x", pady=(8, 0))
        self.button(brow, "COPY REPORT", self.copy_report, CYAN, small=True).pack(side="left")
        self.button(brow, "SAVE .TXT", self.save_report, DIM, small=True).pack(side="left", padx=6)

        # ── DISTRIBUTION ──
        pbox, pin = self.card(right, "// SAMPLING DISTRIBUTION OF  (ȳ − x̄)  STANDARDIZED")
        self.cv_density = tk.Canvas(pin, bg=PANEL, highlightthickness=0, height=170)
        self.cv_density.pack(fill="both", expand=True)

        # ── INTERVAL BAR ──
        bbox, bin_ = self.card(right, "// INTERVAL FOR  μ₂ − μ₁  ON THE DATA AXIS")
        self.cv_bar = tk.Canvas(bin_, bg=PANEL, highlightthickness=0, height=94)
        self.cv_bar.pack(fill="x")

        # ── TABS (packed first at the bottom so they never get clipped) ──
        self.tabs = ttk.Notebook(right)
        self.tabs.pack(side="bottom", fill="x")
        bbox.pack(side="bottom", fill="x", pady=(0, 10))
        pbox.pack(fill="both", expand=True, pady=(0, 10))

        cmp_frame = tk.Frame(self.tabs, bg=PANEL)
        self.tabs.add(cmp_frame, text="COMPARE LEVELS")
        cols = ("level", "crit", "margin", "lower", "upper")
        self.cmp = ttk.Treeview(cmp_frame, columns=cols, show="headings", height=5,
                                selectmode="none")
        for col, text, w in (("level", "CONFIDENCE", 100), ("crit", "CRITICAL", 100),
                             ("margin", "MARGIN", 130), ("lower", "LOWER", 160),
                             ("upper", "UPPER", 160)):
            self.cmp.heading(col, text=text, anchor="w")
            self.cmp.column(col, width=w, anchor="w")
        self.cmp.pack(fill="x", padx=2, pady=2)

        hist_frame = tk.Frame(self.tabs, bg=PANEL)
        self.tabs.add(hist_frame, text="HISTORY")
        hwrap = tk.Frame(hist_frame, bg=PANEL)
        hwrap.pack(fill="x")
        self.hist = ttk.Treeview(hwrap, columns=("time", "inputs", "ci"), show="headings",
                                 height=4)
        for col, text, w in (("time", "TIME", 80), ("inputs", "INPUTS", 400), ("ci", "μ₂ − μ₁", 240)):
            self.hist.heading(col, text=text, anchor="w")
            self.hist.column(col, width=w, anchor="w")
        sb = ttk.Scrollbar(hwrap, orient="vertical", command=self.hist.yview)
        self.hist.configure(yscrollcommand=sb.set)
        self.hist.pack(side="left", fill="x", expand=True)
        sb.pack(side="right", fill="y")
        hbar = tk.Frame(hist_frame, bg=PANEL)
        hbar.pack(fill="x", pady=(4, 2), padx=4)
        self.label(hbar, "double-click a row to restore it", DIM, 8).pack(side="left")
        self.button(hbar, "EXPORT CSV", self.export_history, CYAN, small=True).pack(side="right")
        self.button(hbar, "CLEAR", self.clear_history, DIM, small=True).pack(side="right", padx=6)

    def _wire(self):
        for var in (self.v_n, self.v_xbar, self.v_sx, self.v_m, self.v_ybar, self.v_sy,
                    self.v_sigma, self.v_s1, self.v_s2, self.v_conf, self.v_side, self.v_dec):
            var.trace_add("write", self.schedule)
        self.v_method.trace_add("write", self.on_method)
        for txt in (self.raw_x, self.raw_y):
            for ev in ("<KeyRelease>", "<<Paste>>", "<<Cut>>"):
                txt.bind(ev, self.schedule)
        self.cv_density.bind("<Configure>", lambda e: self.redraw_plots())
        self.cv_bar.bind("<Configure>", lambda e: self.redraw_plots())
        self.hist.bind("<Double-1>", self.restore_history)
        self.bind("<Control-Return>", lambda e: self.calculate(record=True))
        self.bind("<Control-l>", lambda e: self.clear())
        self.bind("<Control-Shift-C>", lambda e: self.copy_report())
        self.n_entry.focus_set()

    # ───────────── toggles ─────────────
    def switch_mode(self):
        if self.v_mode.get() == "summary":
            self.raw_frame.pack_forget()
            self.sum_frame.pack(fill="x")
        else:
            self.sum_frame.pack_forget()
            self.raw_frame.pack(fill="x")
        self.update_rows()
        self.schedule()

    def update_rows(self):
        method = self.v_method.get()
        for widgets, methods in self.row_defs:
            show = methods is None or method in methods
            for w in widgets:
                w.grid() if show else w.grid_remove()
        self.formula_lbl.config(text=FORMULAS[method])

    def on_method(self, *_):
        self.update_rows()
        self.schedule()

    # ───────────── calculation flow ─────────────
    def schedule(self, *_):
        if self._job is not None:
            self.after_cancel(self._job)
        self._job = self.after(120, lambda: self.calculate(record=False))

    def decimals(self):
        try:
            return max(0, min(10, int(self.v_dec.get())))
        except (tk.TclError, ValueError):
            return 4

    def read_sample_raw(self, text_widget, info_label, name):
        raw = text_widget.get("1.0", "end")
        if not norm(raw):
            info_label.config(text="")
            raise Waiting(f"paste the data of sample {name}")
        try:
            data = parse_data(raw)
        except ValueError as e:
            info_label.config(text="")
            raise InputError(f"sample {name}: {e}")
        n = len(data)
        mean = statistics.fmean(data)
        std = statistics.stdev(data) if n >= 2 else None
        info_label.config(text=f"n = {n}   mean = {mean:.4f}   s = " +
                          (f"{std:.4f}" if std is not None else "—"))
        return n, mean, std

    def read_inputs(self):
        method = self.v_method.get()
        sx = sy = None

        if self.v_mode.get() == "raw":
            n, xbar, sx = self.read_sample_raw(self.raw_x, self.info_x, "X")
            m, ybar, sy = self.read_sample_raw(self.raw_y, self.info_y, "Y")
        else:
            need = [self.v_n, self.v_xbar, self.v_m, self.v_ybar]
            if method == "t":
                need += [self.v_sx, self.v_sy]
            if not all(norm(v.get()) for v in need):
                raise Waiting("fill in the sizes and means of both samples" +
                              (" and their std devs" if method == "t" else ""))
            n = to_int(self.v_n.get(), "n")
            m = to_int(self.v_m.get(), "m")
            xbar = to_float(self.v_xbar.get(), "x̄")
            ybar = to_float(self.v_ybar.get(), "ȳ")
            if method == "t":
                sx = to_float(self.v_sx.get(), "sₓ")
                sy = to_float(self.v_sy.get(), "s_y")

        if n < 1 or m < 1:
            raise InputError("n and m must be at least 1")

        sigma = sigma1 = sigma2 = None
        if method == "t":
            if n < 2 or m < 2:
                raise InputError("the pooled t method needs n ≥ 2 and m ≥ 2")
            if sx < 0 or sy < 0:
                raise InputError("standard deviations cannot be negative")
        elif method == "z":
            if not norm(self.v_sigma.get()):
                raise Waiting("enter the known common σ")
            sigma = to_float(self.v_sigma.get(), "σ")
            if sigma <= 0:
                raise InputError("σ must be positive")
        else:
            if not (norm(self.v_s1.get()) and norm(self.v_s2.get())):
                raise Waiting("enter the known σ₁ and σ₂")
            sigma1 = to_float(self.v_s1.get(), "σ₁")
            sigma2 = to_float(self.v_s2.get(), "σ₂")
            if sigma1 <= 0 or sigma2 <= 0:
                raise InputError("σ₁ and σ₂ must be positive")

        if not norm(self.v_conf.get()):
            raise Waiting("enter a confidence level")
        try:
            conf = parse_confidence(self.v_conf.get())
        except ValueError:
            raise InputError("confidence level is not a number")
        if not 0 < conf < 1:
            raise InputError("confidence must be between 0 and 1 (e.g. 0.95 or 95%)")

        return dict(n=n, xbar=xbar, m=m, ybar=ybar, conf=conf, side=self.v_side.get(),
                    method=method, sigma=sigma, sigma1=sigma1, sigma2=sigma2, sx=sx, sy=sy)

    def calculate(self, record=False):
        self._job = None
        try:
            r = compute(**self.read_inputs())
        except Waiting as e:
            self.show_idle(str(e))
            return
        except InputError as e:
            self.show_error(str(e))
            return
        except (ValueError, OverflowError, ZeroDivisionError) as e:
            self.show_error(f"calculation failed: {e}")
            return

        self.last = r
        self.status.config(text="● OK", fg=GREEN)
        self.render(r)
        if record:
            self.add_history(r)

    def show_idle(self, msg):
        self.last = None
        self.status.config(text="… " + msg, fg=DIM)
        self.clear_results()

    def show_error(self, msg):
        self.last = None
        self.status.config(text="✖ " + msg, fg=RED)
        self.clear_results()

    def clear_results(self):
        self.ci_caption.config(text="CONFIDENCE INTERVAL FOR  μ₂ − μ₁")
        self.ci_big.config(text="—", fg=DIM)
        for key, (cap, val) in self.tiles.items():
            cap.config(text=key)
            val.config(text="—")
        self.interp.config(text="")
        self.cmp.delete(*self.cmp.get_children())
        self.redraw_plots()

    # ───────────── rendering ─────────────
    def render(self, r):
        d = self.decimals()
        method = r["method"]
        self.ci_caption.config(text=caption(r))
        self.formula_lbl.config(text=FORMULAS[method])
        self.ci_big.config(text=ci_string(r, d), fg=GREEN)

        sym = "t*" if method == "t" else "z*"
        self.tiles["crit"][0].config(text=f"{sym} critical")
        self.tiles["crit"][1].config(text=f"{r['crit']:.4f}")
        self.tiles["diff"][0].config(text="estimate  ȳ − x̄")
        self.tiles["diff"][1].config(text=f"{r['diff']:.{d}f}")
        self.tiles["se"][0].config(text="standard error")
        self.tiles["se"][1].config(text=f"{r['se']:.{d}f}")
        self.tiles["me"][0].config(text="margin of error")
        self.tiles["me"][1].config(text=f"{r['me']:.{d}f}")
        if method == "t":
            self.tiles["extra"][0].config(text=f"df · sₚ = {r['sp']:.3f}")
            self.tiles["extra"][1].config(text=str(r["df"]))
        elif method == "z":
            self.tiles["extra"][0].config(text="σ  common")
            self.tiles["extra"][1].config(text=f"{r['sigma']:g}")
        else:
            self.tiles["extra"][0].config(text="σ₁ / σ₂")
            self.tiles["extra"][1].config(text=f"{r['sigma1']:g} / {r['sigma2']:g}")

        self.interp.config(text=interpretation(r, d))
        self.fill_compare(r, d)
        self.redraw_plots()

    def fill_compare(self, r, d):
        self.cmp.delete(*self.cmp.get_children())
        levels = list(LEVELS)
        if not any(abs(l - r["conf"]) < 1e-9 for l in levels):
            levels.append(r["conf"])
        for lvl in sorted(levels):
            c = compute(**{**r["inp"], "conf": lvl})
            cur = abs(lvl - r["conf"]) < 1e-9
            self.cmp.insert("", "end", tags=("cur",) if cur else (), values=(
                f"{lvl * 100:g}%", f"{c['crit']:.4f}", f"{c['me']:.{d}f}",
                fmt(c["lower"], d), fmt(c["upper"], d)))
        self.cmp.tag_configure("cur", foreground=GREEN)

    def redraw_plots(self):
        self.draw_density(self.last)
        self.draw_bar(self.last)

    def draw_density(self, r):
        c = self.cv_density
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 80 or h < 80:
            return
        if r is None:
            c.create_text(w / 2, h / 2, text="waiting for valid input…", fill=DIM,
                          font=self.F(11))
            return

        is_t = r["method"] == "t"
        sym = "t" if is_t else "z"
        crit, side = r["crit"], r["side"]
        if is_t:
            df = r["df"]
            pdf = lambda x: float(stats.t.pdf(x, df))
        else:
            pdf = lambda x: float(stats.norm.pdf(x))

        xmax = max(4.5, crit * 1.35)
        pl, pr, pt, pb = 24, 24, 38, 30
        ymax = pdf(0) * 1.12
        X = lambda x: pl + (x + xmax) / (2 * xmax) * (w - pl - pr)
        Y = lambda y: (h - pb) - y / ymax * (h - pb - pt)

        def region(x0, x1, color):
            steps = 60
            pts = [X(x0), Y(0)]
            for i in range(steps + 1):
                x = x0 + (x1 - x0) * i / steps
                pts += [X(x), Y(pdf(x))]
            pts += [X(x1), Y(0)]
            c.create_polygon(pts, fill=color, outline="")

        if side == "two":
            region(-xmax, -crit, TAIL)
            region(crit, xmax, TAIL)
            region(-crit, crit, GREEN_DK)
            markers, tails = [-crit, crit], [(-xmax, -crit), (crit, xmax)]
            tail_p = r["alpha"] / 2
        elif side == "lower":
            region(-xmax, crit, GREEN_DK)
            region(crit, xmax, TAIL)
            markers, tails = [crit], [(crit, xmax)]
            tail_p = r["alpha"]
        else:
            region(-crit, xmax, GREEN_DK)
            region(-xmax, -crit, TAIL)
            markers, tails = [-crit], [(-xmax, -crit)]
            tail_p = r["alpha"]

        c.create_line(pl, Y(0), w - pr, Y(0), fill=BORDER)
        step = 1 if xmax <= 6 else (2 if xmax <= 12 else 5)
        k = -int(xmax) - (-int(xmax) % step)
        while k <= xmax:
            if -xmax <= k <= xmax:
                c.create_line(X(k), Y(0), X(k), Y(0) + 4, fill=DIM)
                c.create_text(X(k), Y(0) + 15, text=str(k), fill=DIM, font=self.F(8))
            k += step

        flat = []
        n_pts = 240
        for i in range(n_pts + 1):
            x = -xmax + 2 * xmax * i / n_pts
            flat += [X(x), Y(pdf(x))]
        c.create_line(flat, fill=GREEN, width=2)

        for mk in markers:
            x = X(mk)
            c.create_line(x, Y(0), x, pt - 4, fill=CYAN, dash=(4, 3))
            lx = min(max(x, pl + 55), w - pr - 55)
            sign = "+" if mk > 0 else "−"
            c.create_text(lx, pt - 14, text=f"{sign}{sym}* = {abs(mk):.3f}", fill=CYAN,
                          font=self.F(9, True))

        for x0, x1 in tails:
            if (X(x1) - X(x0)) >= 46:
                c.create_text((X(x0) + X(x1)) / 2, Y(0) - 12, text=f"{tail_p * 100:.3g}%",
                              fill=RED, font=self.F(9, True))

        c.create_text(X(0), Y(ymax * 0.42), text=f"{r['conf'] * 100:g}%", fill=GREEN,
                      font=self.F(22, True))
        c.create_text(X(0), Y(ymax * 0.42) + 24, text="confidence", fill=DIM, font=self.F(9))

        dist = f"Student t · df = {r['df']}" if is_t else "Standard normal"
        c.create_text(pl, 10, text=dist, anchor="w", fill=DIM, font=self.F(9))
        c.create_text(w - pr, 10, text=f"α = {r['alpha']:.4g}", anchor="e", fill=DIM,
                      font=self.F(9))

    def draw_bar(self, r):
        c = self.cv_bar
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 80 or h < 40:
            return
        if r is None:
            c.create_text(w / 2, h / 2, text="waiting for valid input…", fill=DIM,
                          font=self.F(11))
            return

        d = self.decimals()
        diff, me = r["diff"], r["me"]
        half = me * 1.7 if me > 0 else max(abs(diff) * 0.2, 1.0)
        lo, hi = diff - half, diff + half
        if abs(diff) <= 6 * half:                       # keep 0 in view when reasonable
            lo = min(lo, -0.12 * half)
            hi = max(hi, 0.12 * half)
        pad = 46
        y = h * 0.48
        X = lambda v: pad + (v - lo) / (hi - lo) * (w - 2 * pad)

        c.create_line(pad - 20, y, w - pad + 20, y, fill=BORDER, width=2)
        for i in range(5):
            v = lo + (hi - lo) * i / 4
            c.create_line(X(v), y - 4, X(v), y + 4, fill=DIM)
            c.create_text(X(v), y + 17, text=fmt(v, d), fill=DIM, font=self.F(8))

        left_inf = r["lower"] == -math.inf
        right_inf = r["upper"] == math.inf
        x1 = pad - 20 if left_inf else X(r["lower"])
        x2 = w - pad + 20 if right_inf else X(r["upper"])
        c.create_rectangle(x1, y - 6, x2, y + 6, fill=GREEN_DK, outline=GREEN)

        if not left_inf:
            c.create_line(x1, y - 14, x1, y + 14, fill=GREEN, width=2)
            c.create_text(x1, y - 24, text=fmt(r["lower"], d), fill=GREEN, font=self.F(10, True))
        else:
            c.create_text(x1 + 4, y - 18, text="−∞", fill=GREEN, anchor="w", font=self.F(10, True))
        if not right_inf:
            c.create_line(x2, y - 14, x2, y + 14, fill=GREEN, width=2)
            c.create_text(x2, y - 24, text=fmt(r["upper"], d), fill=GREEN, font=self.F(10, True))
        else:
            c.create_text(x2 - 4, y - 18, text="∞", fill=GREEN, anchor="e", font=self.F(10, True))

        xm = X(diff)
        c.create_oval(xm - 5, y - 5, xm + 5, y + 5, fill=FG, outline=BG)
        c.create_text(xm, y - 24, text=f"ȳ − x̄ = {diff:.{d}f}", fill=FG, font=self.F(9))

        # zero reference: "no difference" (μ₂ = μ₁)
        if lo <= 0 <= hi:
            x0 = X(0)
            c.create_line(x0, y - 30, x0, y + 24, fill=AMBER, dash=(4, 3))
            c.create_text(x0, y + 34, text="0  (μ₂ = μ₁)", fill=AMBER, font=self.F(8, True))
        else:
            side_txt = "← 0" if 0 < lo else "0 →"
            c.create_text(pad - 20 if 0 < lo else w - pad + 20, y + 34, text=side_txt,
                          fill=AMBER, font=self.F(8, True),
                          anchor="w" if 0 < lo else "e")

    # ───────────── history / export ─────────────
    def add_history(self, r):
        rec = dict(r)
        rec["time"] = datetime.now().strftime("%H:%M:%S")
        self.history.append(rec)
        idx = len(self.history) - 1
        tag = {"z": f"z σ={r['sigma']}", "z2": f"z σ₁={r['sigma1']} σ₂={r['sigma2']}",
               "t": "pooled t"}[r["method"]]
        summary = (f"n={r['n']} x̄={r['xbar']:g} | m={r['m']} ȳ={r['ybar']:g} | "
                   f"{r['conf'] * 100:g}% {r['side']} {tag}")
        self.hist.insert("", 0, iid=str(idx),
                         values=(rec["time"], summary, ci_string(r, self.decimals())))

    def restore_history(self, _event=None):
        sel = self.hist.selection()
        if not sel:
            return
        r = self.history[int(sel[0])]
        self.v_mode.set("summary")
        self.switch_mode()
        self.v_n.set(str(r["n"]))
        self.v_xbar.set(repr(r["xbar"]))
        self.v_m.set(str(r["m"]))
        self.v_ybar.set(repr(r["ybar"]))
        self.v_conf.set(f"{r['conf'] * 100:g}")
        self.v_side.set(r["side"])
        self.v_method.set(r["method"])
        for var, key in ((self.v_sigma, "sigma"), (self.v_s1, "sigma1"), (self.v_s2, "sigma2"),
                         (self.v_sx, "sx"), (self.v_sy, "sy")):
            var.set("" if r[key] is None else repr(r[key]))
        self.calculate(record=False)

    def clear_history(self):
        self.history.clear()
        self.hist.delete(*self.hist.get_children())

    def export_history(self):
        if not self.history:
            return self.flash("history is empty")
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")],
                                            initialfile="ci_two_sample_history.csv")
        if not path:
            return
        cols = ["time", "n", "xbar", "m", "ybar", "conf", "side", "method", "sigma", "sigma1",
                "sigma2", "sx", "sy", "sp", "df", "crit", "diff", "se", "me", "lower", "upper"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            wr.writerow(cols)
            for rec in self.history:
                wr.writerow([rec[c] for c in cols])
        self.flash("history exported")

    def copy_report(self):
        if self.last is None:
            return self.flash("nothing to copy yet")
        self.clipboard_clear()
        self.clipboard_append(report_text(self.last, self.decimals()))
        self.flash("report copied to clipboard")

    def save_report(self):
        if self.last is None:
            return self.flash("nothing to save yet")
        path = filedialog.asksaveasfilename(defaultextension=".txt",
                                            filetypes=[("Text", "*.txt")],
                                            initialfile="ci_two_sample_report.txt")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(report_text(self.last, self.decimals()))
        self.flash("report saved")

    def flash(self, msg):
        self.status.config(text="✔ " + msg, fg=CYAN)
        self.after(1800, lambda: self.calculate(record=False))

    # ───────────── misc actions ─────────────
    def clear(self):
        for v in (self.v_n, self.v_xbar, self.v_sx, self.v_m, self.v_ybar, self.v_sy,
                  self.v_sigma, self.v_s1, self.v_s2):
            v.set("")
        self.v_conf.set("95")
        for txt, info in ((self.raw_x, self.info_x), (self.raw_y, self.info_y)):
            txt.delete("1.0", "end")
            info.config(text="")
        self.n_entry.focus_set()
        self.schedule()

    def load_example(self):
        self.v_mode.set("summary")
        self.switch_mode()
        self.v_n.set("25")
        self.v_xbar.set("72")
        self.v_m.set("30")
        self.v_ybar.set("76")
        self.v_sx.set("9")
        self.v_sy.set("10")
        self.v_sigma.set("9.5")
        self.v_s1.set("9")
        self.v_s2.set("10")
        self.v_conf.set("95")
        self.calculate(record=False)


def enable_hidpi():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


if __name__ == "__main__":
    enable_hidpi()
    App().mainloop()
