#!/usr/bin/env python3
"""
Two-Sample Statistics Studio
============================
Confidence interval + hypothesis test for the difference of two means (mu2 - mu1).

  * Z-test      : population standard deviations (sigma1, sigma2) known
  * Welch t-test: unknown sigmas, sample standard deviations, Welch-Satterthwaite df
  * Two-sided / right-tailed / left-tailed, any H0 value (delta0)
  * Input: summary statistics or raw data (paste / CSV import)
  * Live plot: test-statistic distribution with rejection region + CI bar
  * Effect size (Cohen's d), sample-size planner (precision- and power-based)
  * History table with CSV export, copy-to-clipboard, PNG/PDF/SVG plot export
  * Dark ("cyber") and light ("paper") themes
  * Accepts Persian / Arabic digits in every numeric field

Requires: numpy, scipy, matplotlib   (tkinter ships with Python)
"""
from __future__ import annotations

import csv
import math
import re
import sys
import tkinter as tk
import tkinter.font as tkfont
from dataclasses import asdict, dataclass
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import Optional

import matplotlib
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from scipy import stats

matplotlib.rcParams["font.family"] = "monospace"


# =============================================================================
#  CORE  (pure functions, no GUI)
# =============================================================================

_DIGITS = str.maketrans(
    {
        **{chr(0x06F0 + i): str(i) for i in range(10)},  # Persian digits
        **{chr(0x0660 + i): str(i) for i in range(10)},  # Arabic-Indic digits
        "٫": ".",  # Arabic decimal separator
        "٬": "",  # Arabic thousands separator
        "،": ",",  # Arabic comma
        "−": "-",  # unicode minus
    }
)

TAILS = {
    "two": ("Two-sided   (≠)", "≠"),
    "right": ("Right-tailed (>)", ">"),
    "left": ("Left-tailed  (<)", "<"),
}


def normalize(text: str) -> str:
    return text.translate(_DIGITS).strip()


def parse_number(text: str, name: str) -> float:
    cleaned = normalize(text).replace(",", ".")
    try:
        value = float(cleaned)
    except ValueError:
        raise ValueError(f"“{name}” must be a number (got “{text.strip()}”).") from None
    if not math.isfinite(value):
        raise ValueError(f"“{name}” must be a finite number.")
    return value


def parse_int(text: str, name: str) -> int:
    value = parse_number(text, name)
    if value != int(value):
        raise ValueError(f"“{name}” must be a whole number.")
    return int(value)


def parse_data(text: str, name: str) -> list[float]:
    tokens = [t for t in re.split(r"[\s,;]+", normalize(text)) if t]
    values: list[float] = []
    for token in tokens:
        try:
            v = float(token)
        except ValueError:
            raise ValueError(f"{name}: “{token}” is not a number.") from None
        if not math.isfinite(v):
            raise ValueError(f"{name}: “{token}” is not a finite number.")
        values.append(v)
    if not values:
        raise ValueError(f"{name}: no data entered.")
    return values


def summarize(values: list[float]) -> tuple[int, float, float]:
    arr = np.asarray(values, dtype=float)
    n = len(arr)
    sd = float(arr.std(ddof=1)) if n > 1 else float("nan")
    return n, float(arr.mean()), sd


@dataclass(frozen=True)
class Sample:
    n: int
    mean: float
    sd: float  # sigma (Z-test) or s (Welch t-test)


@dataclass
class Result:
    method: str  # "z" | "welch"
    tail: str  # "two" | "right" | "left"
    conf: float
    delta0: float
    n1: int
    n2: int
    mean1: float
    mean2: float
    sd1: float
    sd2: float
    diff: float
    se: float
    df: Optional[float]
    crit: float
    margin: float
    lower: float
    upper: float
    stat: float
    p_value: float
    cohens_d: float
    reject: bool
    time: str = ""


def analyze(
    s1: Sample,
    s2: Sample,
    conf: float,
    method: str = "z",
    tail: str = "two",
    delta0: float = 0.0,
) -> Result:
    if method not in ("z", "welch"):
        raise ValueError("Unknown method.")
    if tail not in TAILS:
        raise ValueError("Unknown alternative hypothesis.")
    if not 0 < conf < 1:
        raise ValueError("Confidence level must be strictly between 0 and 1.")
    for label, s in (("Group 1", s1), ("Group 2", s2)):
        if s.n < 1:
            raise ValueError(f"{label}: sample size must be at least 1.")
        if method == "welch" and s.n < 2:
            raise ValueError(f"{label}: Welch t-test needs at least 2 observations.")
        if not s.sd >= 0:
            raise ValueError(f"{label}: standard deviation must be a number ≥ 0.")

    v1 = s1.sd**2 / s1.n
    v2 = s2.sd**2 / s2.n
    se = math.sqrt(v1 + v2)
    if se == 0:
        raise ValueError("Standard error is 0 (both standard deviations are 0).")

    diff = s2.mean - s1.mean
    alpha = 1.0 - conf

    if method == "z":
        dist = stats.norm
        df: Optional[float] = None
    else:
        df = (v1 + v2) ** 2 / (v1**2 / (s1.n - 1) + v2**2 / (s2.n - 1))
        dist = stats.t(df)

    stat = (diff - delta0) / se

    if tail == "two":
        crit = float(dist.ppf(1 - alpha / 2))
        lower, upper = diff - crit * se, diff + crit * se
        p = 2.0 * float(dist.sf(abs(stat)))
    elif tail == "right":
        crit = float(dist.ppf(conf))
        lower, upper = diff - crit * se, math.inf
        p = float(dist.sf(stat))
    else:
        crit = float(dist.ppf(conf))
        lower, upper = -math.inf, diff + crit * se
        p = float(dist.cdf(stat))
    p = min(p, 1.0)

    dof = s1.n + s2.n - 2
    d = float("nan")
    if dof > 0:
        pooled_sq = ((s1.n - 1) * s1.sd**2 + (s2.n - 1) * s2.sd**2) / dof
        if pooled_sq > 0:
            d = diff / math.sqrt(pooled_sq)

    return Result(
        method=method, tail=tail, conf=conf, delta0=delta0,
        n1=s1.n, n2=s2.n, mean1=s1.mean, mean2=s2.mean, sd1=s1.sd, sd2=s2.sd,
        diff=diff, se=se, df=df, crit=crit, margin=crit * se,
        lower=lower, upper=upper, stat=stat, p_value=p, cohens_d=d,
        reject=p < alpha,
    )


def effect_label(d: float) -> str:
    if math.isnan(d):
        return "n/a"
    a = abs(d)
    if a < 0.2:
        return "negligible"
    if a < 0.5:
        return "small"
    if a < 0.8:
        return "medium"
    return "large"


def n_for_margin(sigma1: float, sigma2: float, conf: float, margin: float) -> int:
    """Per-group n so that the Z confidence interval has half-width <= margin."""
    if sigma1 < 0 or sigma2 < 0 or sigma1 == sigma2 == 0:
        raise ValueError("Standard deviations must be ≥ 0 and not both 0.")
    if not 0 < conf < 1:
        raise ValueError("Confidence level must be strictly between 0 and 1.")
    if margin <= 0:
        raise ValueError("Margin of error must be greater than 0.")
    z = stats.norm.ppf(1 - (1 - conf) / 2)
    return math.ceil(z**2 * (sigma1**2 + sigma2**2) / margin**2)


def n_for_power(
    sigma1: float, sigma2: float, delta: float, alpha: float, power: float, two_sided: bool = True
) -> int:
    """Per-group n for a Z-test to detect a true difference `delta` with given power."""
    if sigma1 < 0 or sigma2 < 0 or sigma1 == sigma2 == 0:
        raise ValueError("Standard deviations must be ≥ 0 and not both 0.")
    if delta == 0:
        raise ValueError("The difference to detect must be non-zero.")
    if not (0 < alpha < 1 and 0 < power < 1):
        raise ValueError("α and power must be strictly between 0 and 1.")
    za = stats.norm.ppf(1 - alpha / 2) if two_sided else stats.norm.ppf(1 - alpha)
    zb = stats.norm.ppf(power)
    return math.ceil((za + zb) ** 2 * (sigma1**2 + sigma2**2) / delta**2)


def fmt(v: Optional[float], digits: int = 4) -> str:
    if v is None:
        return "–"
    if math.isnan(v):
        return "n/a"
    if math.isinf(v):
        return "+∞" if v > 0 else "−∞"
    return f"{v:.{digits}f}"


def fmt_p(p: float) -> str:
    return f"{p:.2e}" if p < 1e-4 else f"{p:.4f}"


def format_summary(r: Result) -> str:
    sym = TAILS[r.tail][1]
    alpha = 1 - r.conf
    name = "Z-test (σ known)" if r.method == "z" else "Welch t-test (σ unknown)"
    sd_name = "σ" if r.method == "z" else "s"
    lines = [
        f"Method        : {name}",
        f"H0 / H1       : μ2 − μ1 = {r.delta0:g}   /   μ2 − μ1 {sym} {r.delta0:g}",
        f"Group 1       : n = {r.n1}, mean = {r.mean1:.4f}, {sd_name} = {r.sd1:.4f}",
        f"Group 2       : n = {r.n2}, mean = {r.mean2:.4f}, {sd_name} = {r.sd2:.4f}",
        f"Difference    : {fmt(r.diff)}   (mean2 − mean1)",
        f"Std. error    : {fmt(r.se)}",
    ]
    if r.df is not None:
        lines.append(f"Welch df      : {r.df:.2f}")
    lines += [
        f"Critical value: {fmt(r.crit)}",
        f"Margin        : {fmt(r.margin)}",
        f"{r.conf * 100:g}% CI        : ({fmt(r.lower)}, {fmt(r.upper)})",
        f"Statistic     : {fmt(r.stat)}",
        f"p-value       : {fmt_p(r.p_value)}",
        f"Cohen's d     : {fmt(r.cohens_d, 3)} ({effect_label(r.cohens_d)})",
        f"Decision      : {'Reject H0' if r.reject else 'Fail to reject H0'} at α = {alpha:.4g}",
    ]
    return "\n".join(lines)


# =============================================================================
#  GUI
# =============================================================================

THEMES = {
    "dark": dict(
        bg="#0a0e0f", panel="#0f1517", fg="#c9d1d3", muted="#5f7276", grid="#1f2c2f",
        accent="#2ee59d", accent_fg="#06100c", accent_hover="#5df0b6", cyan="#22d3ee",
        reject="#ff6b6b", ok="#2ee59d",
    ),
    "paper": dict(
        bg="#f1efe9", panel="#fbfaf6", fg="#141414", muted="#6b6b66", grid="#cfcdc4",
        accent="#141414", accent_fg="#f1efe9", accent_hover="#3a3a36", cyan="#0e7490",
        reject="#b91c1c", ok="#166534",
    ),
}

RESULT_ROWS = [
    ("diff", "Difference (Y − X)"),
    ("se", "Standard error"),
    ("stat", "Test statistic"),
    ("p", "p-value"),
    ("crit", "Critical value"),
    ("df", "Degrees of freedom"),
    ("margin", "Margin of error"),
    ("lower", "CI lower bound"),
    ("upper", "CI upper bound"),
    ("d", "Cohen's d"),
]

HELP_TEXT = """\
Difference estimated:  Y − X  =  mean2 − mean1

Z-test (σ known)
  SE  = √(σ₁²/n₁ + σ₂²/n₂)
  z   = (Y − X − δ₀) / SE
  CI  = (Y − X) ± z* · SE        z* = Φ⁻¹(1 − α/2)   (one-sided: Φ⁻¹(1 − α))

Welch t-test (σ unknown, no equal-variance assumption)
  SE  = √(s₁²/n₁ + s₂²/n₂)
  df  = (v₁ + v₂)² / (v₁²/(n₁−1) + v₂²/(n₂−1)),   v = s²/n
  CI  = (Y − X) ± t*(df) · SE

One-sided intervals are open-ended (−∞ or +∞), matching the tail.
α = 1 − confidence level; reject H₀ when p < α.
Cohen's d uses the pooled standard deviation.

Raw-data mode: n, mean and s are computed from the pasted numbers
(separate by spaces, commas, semicolons or new lines).
With the Z-test you still enter the known σ for each group.

Shortcuts:  F5 / Ctrl+Enter = calculate     F8 = switch theme
"""


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Two-Sample Statistics Studio")
        self.geometry("1200x800")
        self.minsize(1040, 720)

        self.theme = "dark"
        self.history: list[Result] = []
        self.last: Optional[Result] = None
        self.text_widgets: list[tk.Text] = []
        self.status = tk.StringVar(value="Ready — fill in the inputs and press Calculate (F5).")

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self._setup_fonts()

        self.method_var = tk.StringVar(value="z")
        self.source_var = tk.StringVar(value="summary")
        self.tail_var = tk.StringVar(value=TAILS["two"][0])
        self.rv = {k: tk.StringVar(value="–") for k, _ in RESULT_ROWS}

        self._build_menu()
        ttk.Label(self, textvariable=self.status, style="Muted.TLabel", anchor="w", padding=(10, 4)).pack(
            side="bottom", fill="x"
        )
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        tab_a, tab_p, tab_h = ttk.Frame(nb), ttk.Frame(nb), ttk.Frame(nb)
        nb.add(tab_a, text="  Analysis  ")
        nb.add(tab_p, text="  Sample-size planner  ")
        nb.add(tab_h, text="  History  ")
        self._build_analysis(tab_a)
        self._build_planner(tab_p)
        self._build_history(tab_h)

        self.bind("<F5>", lambda e: self.calculate())
        self.bind("<Control-Return>", lambda e: self.calculate())
        self.bind("<F8>", lambda e: self.toggle_theme())

        self.apply_theme()
        self._refresh_mode()
        self._update_hyp()

    # ------------------------------------------------------------------ setup
    def _setup_fonts(self) -> None:
        avail = set(tkfont.families(self))
        family = next(
            (f for f in ("JetBrains Mono", "Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Menlo", "Courier New")
             if f in avail),
            tkfont.nametofont("TkFixedFont").actual("family"),
        )
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkFixedFont"):
            tkfont.nametofont(name).configure(family=family, size=10)
        self.f_bold = tkfont.Font(family=family, size=10, weight="bold")
        self.f_big = tkfont.Font(family=family, size=13, weight="bold")
        self.f_mono = tkfont.nametofont("TkFixedFont")

    def _build_menu(self) -> None:
        mb = tk.Menu(self)
        fm = tk.Menu(mb, tearoff=0)
        fm.add_command(label="Load two-column CSV…", command=self.load_csv)
        fm.add_command(label="Export history to CSV…", command=self.export_history)
        fm.add_command(label="Save plot…", command=self.save_plot)
        fm.add_separator()
        fm.add_command(label="Quit", command=self.destroy)
        mb.add_cascade(label="File", menu=fm)
        vm = tk.Menu(mb, tearoff=0)
        vm.add_command(label="Switch theme (dark / paper)", accelerator="F8", command=self.toggle_theme)
        mb.add_cascade(label="View", menu=vm)
        hm = tk.Menu(mb, tearoff=0)
        hm.add_command(label="Formulas & notes", command=self.show_help)
        mb.add_cascade(label="Help", menu=hm)
        self.config(menu=mb)

    # --------------------------------------------------------------- analysis
    def _build_analysis(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(0, weight=1)
        left = ttk.Frame(tab, padding=(10, 10, 4, 10))
        left.grid(row=0, column=0, sticky="ns")
        right = ttk.Frame(tab, padding=(4, 10, 10, 10))
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        # ---- settings
        st = ttk.LabelFrame(left, text=" SETTINGS ", padding=10)
        st.grid(row=0, column=0, sticky="ew")
        ttk.Label(st, text="Method").grid(row=0, column=0, sticky="nw", pady=2)
        ttk.Radiobutton(st, text="Z-test  (σ known)", value="z", variable=self.method_var,
                        command=self._refresh_mode).grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(st, text="Welch t  (σ unknown)", value="welch", variable=self.method_var,
                        command=self._refresh_mode).grid(row=1, column=1, sticky="w")
        ttk.Label(st, text="Alternative").grid(row=2, column=0, sticky="w", pady=(6, 2))
        cb = ttk.Combobox(st, textvariable=self.tail_var, state="readonly", width=17,
                          values=[v[0] for v in TAILS.values()])
        cb.grid(row=2, column=1, sticky="w", pady=(6, 2))
        cb.bind("<<ComboboxSelected>>", lambda e: self._update_hyp())
        ttk.Label(st, text="Confidence").grid(row=3, column=0, sticky="w", pady=2)
        self.conf_e = ttk.Entry(st, width=10)
        self.conf_e.grid(row=3, column=1, sticky="w", pady=2)
        self.conf_e.insert(0, "0.95")
        ttk.Label(st, text="H₀ value δ₀").grid(row=4, column=0, sticky="w", pady=2)
        self.delta_e = ttk.Entry(st, width=10)
        self.delta_e.grid(row=4, column=1, sticky="w", pady=2)
        self.delta_e.insert(0, "0")
        self.delta_e.bind("<KeyRelease>", lambda e: self._update_hyp())
        for e in (self.conf_e, self.delta_e):
            e.bind("<Return>", lambda ev: self.calculate())
        ttk.Label(st, text="Data source").grid(row=5, column=0, sticky="nw", pady=(6, 2))
        ttk.Radiobutton(st, text="Summary statistics", value="summary", variable=self.source_var,
                        command=self._refresh_mode).grid(row=5, column=1, sticky="w", pady=(6, 0))
        ttk.Radiobutton(st, text="Raw data", value="raw", variable=self.source_var,
                        command=self._refresh_mode).grid(row=6, column=1, sticky="w")
        self.hyp_lbl = ttk.Label(st, style="Cyan.TLabel", justify="left")
        self.hyp_lbl.grid(row=7, column=0, columnspan=2, sticky="w", pady=(10, 0))
        for w in st.grid_slaves(column=0):
            if w is not self.hyp_lbl:
                w.grid_configure(padx=(0, 12))

        # ---- groups
        self.g1 = self._build_group(left, " GROUP 1  (X) ", "Group 1")
        self.g1["box"].grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.g2 = self._build_group(left, " GROUP 2  (Y) ", "Group 2")
        self.g2["box"].grid(row=2, column=0, sticky="ew", pady=(8, 0))

        # ---- buttons
        bf = ttk.Frame(left)
        bf.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(bf, text="CALCULATE", style="Accent.TButton", command=self.calculate).pack(
            side="left", fill="x", expand=True)
        ttk.Button(bf, text="Clear", command=self.clear).pack(side="left", padx=(6, 0))
        ttk.Button(bf, text="Example", command=self.load_example).pack(side="left", padx=(6, 0))

        # ---- verdict
        self.verdict = ttk.Label(right, text="", style="Verdict.TLabel", anchor="w")
        self.verdict.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        # ---- results
        rb = ttk.LabelFrame(right, text=" RESULTS ", padding=10)
        rb.grid(row=1, column=0, sticky="ew")
        half = (len(RESULT_ROWS) + 1) // 2
        for i, (key, label) in enumerate(RESULT_ROWS):
            r, c = i % half, (i // half) * 2
            ttk.Label(rb, text=label).grid(row=r, column=c, sticky="w", padx=(0 if c == 0 else 26, 8), pady=2)
            ttk.Label(rb, textvariable=self.rv[key], font=self.f_bold, width=20, anchor="e").grid(
                row=r, column=c + 1, sticky="e")
        self.ci_lbl = ttk.Label(rb, text="", style="Big.TLabel")
        self.ci_lbl.grid(row=half, column=0, columnspan=4, sticky="w", pady=(8, 0))

        # ---- plot
        pf = ttk.Frame(right)
        pf.grid(row=2, column=0, sticky="nsew", pady=(8, 0))
        self.fig = Figure(figsize=(6, 4.6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=pf)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # ---- output buttons
        of = ttk.Frame(right)
        of.grid(row=3, column=0, sticky="e", pady=(8, 0))
        ttk.Button(of, text="Copy summary", command=self.copy_summary).pack(side="left")
        ttk.Button(of, text="Save plot…", command=self.save_plot).pack(side="left", padx=(6, 0))

    def _build_group(self, parent: ttk.Frame, title: str, short: str) -> dict:
        box = ttk.LabelFrame(parent, text=title, padding=10)
        g: dict = {"box": box, "short": short, "ents": {}}

        g["summ"] = ttk.Frame(box)
        g["summ"].grid(row=0, column=0, sticky="w")
        for r, (key, label) in enumerate((("n", "Sample size  n"), ("mean", "Mean"))):
            ttk.Label(g["summ"], text=label, width=20).grid(row=r, column=0, sticky="w", pady=2)
            e = ttk.Entry(g["summ"], width=14)
            e.grid(row=r, column=1, pady=2)
            e.bind("<Return>", lambda ev: self.calculate())
            g["ents"][key] = e

        g["raw"] = ttk.Frame(box)
        g["raw"].grid(row=0, column=0, sticky="w")
        txt = tk.Text(g["raw"], width=32, height=5, wrap="word", relief="flat", borderwidth=0,
                      highlightthickness=1, font=self.f_mono)
        sb = ttk.Scrollbar(g["raw"], orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        txt.grid(row=0, column=0)
        sb.grid(row=0, column=1, sticky="ns")
        g["info"] = ttk.Label(g["raw"], text="", style="Muted.TLabel")
        g["info"].grid(row=1, column=0, columnspan=2, sticky="w", pady=(3, 0))
        g["text"] = txt
        self.text_widgets.append(txt)

        g["sdf"] = ttk.Frame(box)
        g["sdf"].grid(row=1, column=0, sticky="w", pady=(4, 0))
        g["sd_lbl"] = ttk.Label(g["sdf"], text="σ  (population std)", width=20)
        g["sd_lbl"].grid(row=0, column=0, sticky="w")
        g["sd"] = ttk.Entry(g["sdf"], width=14)
        g["sd"].grid(row=0, column=1)
        g["sd"].bind("<Return>", lambda ev: self.calculate())
        return g

    def _refresh_mode(self) -> None:
        raw = self.source_var.get() == "raw"
        z = self.method_var.get() == "z"
        for g in (self.g1, self.g2):
            if raw:
                g["summ"].grid_remove()
                g["raw"].grid()
            else:
                g["raw"].grid_remove()
                g["summ"].grid()
            g["sd_lbl"].configure(text="σ  (population std)" if z else "s  (sample std)")
            if raw and not z:
                g["sdf"].grid_remove()  # s comes from the data itself
            else:
                g["sdf"].grid()

    def _tail_key(self) -> str:
        label = self.tail_var.get()
        for key, (lab, _) in TAILS.items():
            if lab == label:
                return key
        return "two"

    def _update_hyp(self) -> None:
        try:
            d = f"{parse_number(self.delta_e.get(), 'δ₀'):g}"
        except ValueError:
            d = "δ₀"
        sym = TAILS[self._tail_key()][1]
        self.hyp_lbl.configure(text=f"H₀:  μ₂ − μ₁ = {d}\nH₁:  μ₂ − μ₁ {sym} {d}")

    # ------------------------------------------------------------ computation
    def _collect(self):
        method = self.method_var.get()
        tail = self._tail_key()
        conf = parse_number(self.conf_e.get(), "Confidence level")
        delta0 = parse_number(self.delta_e.get(), "H₀ value δ₀")
        raw = self.source_var.get() == "raw"
        sd_sym = "σ" if method == "z" else "s"
        samples = []
        for g in (self.g1, self.g2):
            name = g["short"]
            if raw:
                n, mean, s = summarize(parse_data(g["text"].get("1.0", "end"), name))
                shown_s = f"{s:.4f}" if n > 1 else "n/a"
                g["info"].configure(text=f"n = {n}   mean = {mean:.4f}   s = {shown_s}")
                sd = s if method == "welch" else parse_number(g["sd"].get(), f"{name} σ")
            else:
                n = parse_int(g["ents"]["n"].get(), f"{name} sample size")
                mean = parse_number(g["ents"]["mean"].get(), f"{name} mean")
                sd = parse_number(g["sd"].get(), f"{name} {sd_sym}")
            samples.append(Sample(n, mean, sd))
        return samples[0], samples[1], conf, method, tail, delta0

    def calculate(self) -> None:
        try:
            res = analyze(*self._collect())
        except ValueError as exc:
            messagebox.showerror("Input error", str(exc))
            return
        res.time = datetime.now().strftime("%H:%M:%S")
        self.last = res
        self.history.append(res)
        self._add_history_row(len(self.history), res)
        self._show(res)
        self.status.set(
            f"{'Reject' if res.reject else 'Fail to reject'} H₀  ·  p = {fmt_p(res.p_value)}  ·  "
            f"{res.conf * 100:g}% CI ({fmt(res.lower)}, {fmt(res.upper)})"
        )

    # ---------------------------------------------------------------- display
    def _show(self, r: Result) -> None:
        t = THEMES[self.theme]
        self.rv["diff"].set(fmt(r.diff))
        self.rv["se"].set(fmt(r.se))
        self.rv["stat"].set(fmt(r.stat))
        self.rv["p"].set(fmt_p(r.p_value))
        self.rv["crit"].set(fmt(r.crit))
        self.rv["df"].set("∞  (normal)" if r.df is None else f"{r.df:.2f}")
        self.rv["margin"].set(fmt(r.margin))
        self.rv["lower"].set(fmt(r.lower))
        self.rv["upper"].set(fmt(r.upper))
        self.rv["d"].set("n/a" if math.isnan(r.cohens_d) else f"{r.cohens_d:.3f} ({effect_label(r.cohens_d)})")

        alpha = 1 - r.conf
        if r.reject:
            self.verdict.configure(
                text=f"REJECT H₀   ·   p = {fmt_p(r.p_value)}  <  α = {alpha:.4g}", foreground=t["reject"])
        else:
            self.verdict.configure(
                text=f"FAIL TO REJECT H₀   ·   p = {fmt_p(r.p_value)}  ≥  α = {alpha:.4g}", foreground=t["ok"])
        kind = "" if r.tail == "two" else "one-sided "
        self.ci_lbl.configure(text=f"{r.conf * 100:g}% {kind}CI for μ₂ − μ₁:   ({fmt(r.lower)},  {fmt(r.upper)})")
        self._draw(r)

    def _reset_results(self) -> None:
        t = THEMES[self.theme]
        for var in self.rv.values():
            var.set("–")
        self.verdict.configure(text="No analysis yet", foreground=t["muted"])
        self.ci_lbl.configure(text="")
        self._draw(None)

    def _style_axes(self, ax) -> None:
        t = THEMES[self.theme]
        ax.set_facecolor(t["panel"])
        for side, spine in ax.spines.items():
            spine.set_color(t["grid"])
            if side in ("top", "right"):
                spine.set_visible(False)
        ax.tick_params(colors=t["muted"], labelsize=8)
        ax.title.set_color(t["fg"])
        ax.title.set_fontsize(9)

    def _draw(self, r: Optional[Result]) -> None:
        t = THEMES[self.theme]
        self.fig.clear()
        self.fig.set_facecolor(t["panel"])
        self.canvas.get_tk_widget().configure(bg=t["panel"], highlightthickness=0)
        gs = self.fig.add_gridspec(2, 1, height_ratios=[3, 1.25], hspace=0.7,
                                   left=0.06, right=0.97, top=0.92, bottom=0.12)
        ax1 = self.fig.add_subplot(gs[0])
        ax2 = self.fig.add_subplot(gs[1])

        if r is None:
            ax1.axis("off")
            ax2.axis("off")
            ax1.text(0.5, 0.5, "run an analysis to see the plot", ha="center", va="center",
                     color=t["muted"], transform=ax1.transAxes)
            self.canvas.draw_idle()
            return

        # ---- top: distribution of the test statistic under H0
        dist = stats.norm if r.df is None else stats.t(r.df)
        lim = max(4.0, abs(r.stat) + 1.0)
        x = np.linspace(-lim, lim, 800)
        y = dist.pdf(x)
        alpha = 1 - r.conf
        ax1.plot(x, y, color=t["fg"], lw=1.4)
        shade = dict(color=t["reject"], alpha=0.45, lw=0)
        if r.tail == "two":
            c = float(dist.ppf(1 - alpha / 2))
            ax1.fill_between(x, y, where=(x <= -c), label="rejection region", **shade)
            ax1.fill_between(x, y, where=(x >= c), **shade)
        elif r.tail == "right":
            c = float(dist.ppf(1 - alpha))
            ax1.fill_between(x, y, where=(x >= c), label="rejection region", **shade)
        else:
            c = float(dist.ppf(alpha))
            ax1.fill_between(x, y, where=(x <= c), label="rejection region", **shade)
        ax1.axvline(r.stat, color=t["accent"], lw=2, label=f"statistic = {r.stat:.3f}")
        dist_name = "Z" if r.df is None else f"t (df = {r.df:.1f})"
        ax1.set_title(f"Test statistic under H₀  ·  {dist_name}")
        ax1.set_yticks([])
        ax1.set_xlim(-lim, lim)
        self._style_axes(ax1)
        leg = ax1.legend(frameon=False, fontsize=8, loc="upper left")
        for txt in leg.get_texts():
            txt.set_color(t["fg"])

        # ---- bottom: confidence interval bar
        reach = 2 * abs(r.margin)
        lo = r.lower if math.isfinite(r.lower) else r.diff - reach
        hi = r.upper if math.isfinite(r.upper) else r.diff + reach
        left_edge = min(lo, hi, r.delta0, r.diff)
        right_edge = max(lo, hi, r.delta0, r.diff)
        pad = 0.18 * max(right_edge - left_edge, 1e-12)
        ax2.plot([lo, hi], [0, 0], color=t["cyan"], lw=6, solid_capstyle="round")
        if not math.isfinite(r.lower):
            ax2.plot([lo], [0], marker="<", color=t["cyan"], ms=11)
        if not math.isfinite(r.upper):
            ax2.plot([hi], [0], marker=">", color=t["cyan"], ms=11)
        ax2.axvline(r.delta0, color=t["muted"], ls="--", lw=1.4)
        ax2.plot([r.diff], [0], "o", ms=9, mfc=t["panel"], mec=t["accent"], mew=2.2, zorder=5)
        for val in (r.lower, r.upper):
            if math.isfinite(val):
                ax2.annotate(f"{val:.3f}", (val, 0), xytext=(0, -17), textcoords="offset points",
                             ha="center", fontsize=8, color=t["fg"])
        ax2.annotate(f"{r.diff:.3f}", (r.diff, 0), xytext=(0, 10), textcoords="offset points",
                     ha="center", fontsize=8, color=t["accent"])
        ax2.set_xlim(left_edge - pad, right_edge + pad)
        ax2.set_ylim(-1, 1)
        ax2.set_yticks([])
        ax2.set_title(f"{r.conf * 100:g}% CI for μ₂ − μ₁   (dashed line = H₀ value)")
        self._style_axes(ax2)
        self.canvas.draw_idle()

    # ----------------------------------------------------------------- theme
    def apply_theme(self) -> None:
        t = THEMES[self.theme]
        s = self.style
        self.configure(bg=t["bg"])
        s.configure(".", background=t["bg"], foreground=t["fg"], fieldbackground=t["panel"],
                    bordercolor=t["grid"], lightcolor=t["bg"], darkcolor=t["bg"],
                    troughcolor=t["panel"], focuscolor=t["bg"], insertcolor=t["fg"])
        s.configure("TLabelframe", background=t["bg"], bordercolor=t["grid"])
        s.configure("TLabelframe.Label", background=t["bg"], foreground=t["muted"], font=self.f_bold)
        s.configure("TButton", background=t["panel"], foreground=t["fg"], padding=(10, 6), bordercolor=t["grid"])
        s.map("TButton", background=[("active", t["grid"])])
        s.configure("Accent.TButton", background=t["accent"], foreground=t["accent_fg"], font=self.f_bold)
        s.map("Accent.TButton", background=[("active", t["accent_hover"])],
              foreground=[("active", t["accent_fg"])])
        s.configure("TEntry", fieldbackground=t["panel"], foreground=t["fg"], bordercolor=t["grid"], padding=3)
        s.map("TEntry", bordercolor=[("focus", t["accent"])])
        s.configure("TCombobox", fieldbackground=t["panel"], background=t["panel"], foreground=t["fg"],
                    arrowcolor=t["fg"], bordercolor=t["grid"], padding=3)
        s.map("TCombobox", fieldbackground=[("readonly", t["panel"])], foreground=[("readonly", t["fg"])],
              selectbackground=[("readonly", t["panel"])], selectforeground=[("readonly", t["fg"])])
        s.configure("TRadiobutton", background=t["bg"], foreground=t["fg"],
                    indicatorbackground=t["panel"], indicatorforeground=t["accent"],
                    upperbordercolor=t["muted"], lowerbordercolor=t["muted"])
        s.map("TRadiobutton", background=[("active", t["bg"])],
              indicatorbackground=[("pressed", t["panel"]), ("!disabled", t["panel"])],
              indicatorforeground=[("selected", t["accent"]), ("!selected", t["panel"])],
              upperbordercolor=[("!disabled", t["muted"])], lowerbordercolor=[("!disabled", t["muted"])])
        s.configure("TNotebook", background=t["bg"], bordercolor=t["grid"], tabmargins=(8, 6, 8, 0))
        s.configure("TNotebook.Tab", background=t["panel"], foreground=t["muted"], padding=(14, 6),
                    bordercolor=t["grid"])
        s.map("TNotebook.Tab", background=[("selected", t["bg"])], foreground=[("selected", t["accent"])])
        s.configure("Treeview", background=t["panel"], fieldbackground=t["panel"], foreground=t["fg"],
                    rowheight=26, bordercolor=t["grid"])
        s.configure("Treeview.Heading", background=t["grid"], foreground=t["fg"], font=self.f_bold)
        s.map("Treeview", background=[("selected", t["accent"])], foreground=[("selected", t["accent_fg"])])
        s.configure("Vertical.TScrollbar", background=t["grid"], troughcolor=t["panel"],
                    arrowcolor=t["fg"], bordercolor=t["grid"])
        s.configure("Muted.TLabel", foreground=t["muted"])
        s.configure("Cyan.TLabel", foreground=t["cyan"], font=self.f_bold)
        s.configure("Big.TLabel", foreground=t["accent"], font=self.f_big)
        s.configure("Verdict.TLabel", font=self.f_big)
        for txt in self.text_widgets:
            txt.configure(bg=t["panel"], fg=t["fg"], insertbackground=t["accent"],
                          highlightbackground=t["grid"], highlightcolor=t["accent"],
                          selectbackground=t["accent"], selectforeground=t["accent_fg"])
        self.option_add("*TCombobox*Listbox.background", t["panel"])
        self.option_add("*TCombobox*Listbox.foreground", t["fg"])
        self.option_add("*TCombobox*Listbox.selectBackground", t["accent"])
        self.option_add("*TCombobox*Listbox.selectForeground", t["accent_fg"])
        self.option_add("*TCombobox*Listbox.font", self.f_mono)
        if self.last is not None:
            self._show(self.last)
        else:
            self._reset_results()
        self._plan_theme()

    def toggle_theme(self) -> None:
        self.theme = "paper" if self.theme == "dark" else "dark"
        self.apply_theme()

    # --------------------------------------------------------------- planner
    def _plan_theme(self) -> None:
        pass  # planner uses ttk styles only

    def _entry_rows(self, parent: ttk.Frame, rows) -> dict:
        entries = {}
        for r, (key, label, default) in enumerate(rows):
            ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", pady=3)
            e = ttk.Entry(parent, width=14)
            e.grid(row=r, column=1, padx=(12, 0), pady=3)
            e.insert(0, default)
            entries[key] = e
        return entries

    def _build_planner(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(0, weight=1)

        a = ttk.LabelFrame(tab, text=" A · SAMPLE SIZE FOR A TARGET MARGIN OF ERROR  (Z, equal n per group) ",
                           padding=14)
        a.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        self.pa = self._entry_rows(a, [
            ("s1", "σ₁  (group 1)", ""), ("s2", "σ₂  (group 2)", ""),
            ("conf", "Confidence level", "0.95"), ("E", "Desired margin  ±E", ""),
        ])
        ttk.Button(a, text="COMPUTE", style="Accent.TButton", command=self.plan_margin).grid(
            row=0, column=2, padx=24, sticky="n", pady=3)
        self.pa_out = ttk.Label(a, text="", style="Big.TLabel")
        self.pa_out.grid(row=4, column=0, columnspan=3, sticky="w", pady=(10, 0))

        b = ttk.LabelFrame(tab, text=" B · SAMPLE SIZE FOR A TARGET POWER  (Z, equal n per group) ", padding=14)
        b.grid(row=1, column=0, sticky="ew", padx=14, pady=8)
        self.pb = self._entry_rows(b, [
            ("s1", "σ₁  (group 1)", ""), ("s2", "σ₂  (group 2)", ""),
            ("delta", "True difference to detect  δ", ""), ("alpha", "Significance level  α", "0.05"),
            ("power", "Power  (1 − β)", "0.80"),
        ])
        ttk.Label(b, text="Test").grid(row=5, column=0, sticky="w", pady=3)
        self.pb_tail = ttk.Combobox(b, state="readonly", width=12, values=["Two-sided", "One-sided"])
        self.pb_tail.current(0)
        self.pb_tail.grid(row=5, column=1, padx=(12, 0), pady=3)
        ttk.Button(b, text="COMPUTE", style="Accent.TButton", command=self.plan_power).grid(
            row=0, column=2, padx=24, sticky="n", pady=3)
        self.pb_out = ttk.Label(b, text="", style="Big.TLabel")
        self.pb_out.grid(row=6, column=0, columnspan=3, sticky="w", pady=(10, 0))

    def plan_margin(self) -> None:
        try:
            n = n_for_margin(
                parse_number(self.pa["s1"].get(), "σ₁"), parse_number(self.pa["s2"].get(), "σ₂"),
                parse_number(self.pa["conf"].get(), "Confidence level"),
                parse_number(self.pa["E"].get(), "Margin ±E"),
            )
        except ValueError as exc:
            messagebox.showerror("Input error", str(exc))
            return
        self.pa_out.configure(text=f"n ≥ {n} per group    (total {2 * n})")

    def plan_power(self) -> None:
        try:
            n = n_for_power(
                parse_number(self.pb["s1"].get(), "σ₁"), parse_number(self.pb["s2"].get(), "σ₂"),
                parse_number(self.pb["delta"].get(), "δ"), parse_number(self.pb["alpha"].get(), "α"),
                parse_number(self.pb["power"].get(), "Power"),
                two_sided=self.pb_tail.get() == "Two-sided",
            )
        except ValueError as exc:
            messagebox.showerror("Input error", str(exc))
            return
        self.pb_out.configure(text=f"n ≥ {n} per group    (total {2 * n})")

    # --------------------------------------------------------------- history
    def _build_history(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)
        cols = ("no", "time", "method", "alt", "n1", "n2", "diff", "ci", "stat", "p", "decision")
        heads = ("#", "Time", "Method", "H₁", "n₁", "n₂", "Y − X", "Confidence interval", "Statistic",
                 "p-value", "Decision")
        widths = (40, 80, 70, 40, 55, 55, 100, 230, 100, 100, 150)
        self.tree = ttk.Treeview(tab, columns=cols, show="headings")
        for c, h, w in zip(cols, heads, widths):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="center", stretch=(c == "ci"))
        vsb = ttk.Scrollbar(tab, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(14, 0), pady=14)
        vsb.grid(row=0, column=1, sticky="ns", pady=14, padx=(0, 14))
        self.tree.bind("<Double-1>", self._history_detail)
        bf = ttk.Frame(tab)
        bf.grid(row=1, column=0, columnspan=2, sticky="e", padx=14, pady=(0, 14))
        ttk.Label(bf, text="double-click a row for full details", style="Muted.TLabel").pack(side="left", padx=12)
        ttk.Button(bf, text="Export CSV…", command=self.export_history).pack(side="left")
        ttk.Button(bf, text="Clear history", command=self.clear_history).pack(side="left", padx=(6, 0))

    def _add_history_row(self, no: int, r: Result) -> None:
        self.tree.insert("", "end", values=(
            no, r.time, "Z" if r.method == "z" else "Welch", TAILS[r.tail][1], r.n1, r.n2,
            fmt(r.diff), f"({fmt(r.lower)}, {fmt(r.upper)})", fmt(r.stat), fmt_p(r.p_value),
            "Reject H₀" if r.reject else "Fail to reject",
        ))

    def _history_detail(self, _event) -> None:
        sel = self.tree.selection()
        if sel:
            idx = int(self.tree.item(sel[0], "values")[0]) - 1
            messagebox.showinfo("Analysis details", format_summary(self.history[idx]))

    def clear_history(self) -> None:
        self.history.clear()
        self.tree.delete(*self.tree.get_children())
        self.status.set("History cleared.")

    def export_history(self) -> None:
        if not self.history:
            messagebox.showinfo("Export", "History is empty.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        rows = [asdict(r) for r in self.history]
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        self.status.set(f"Exported {len(rows)} rows → {path}")

    # ------------------------------------------------------------ misc actions
    def _set(self, entry: ttk.Entry, value: str) -> None:
        entry.delete(0, "end")
        entry.insert(0, value)

    def clear(self) -> None:
        for g in (self.g1, self.g2):
            for e in g["ents"].values():
                e.delete(0, "end")
            g["sd"].delete(0, "end")
            g["text"].delete("1.0", "end")
            g["info"].configure(text="")
        self._set(self.conf_e, "0.95")
        self._set(self.delta_e, "0")
        self.last = None
        self._reset_results()
        self._update_hyp()
        self.status.set("Inputs cleared.")

    def load_example(self) -> None:
        self.source_var.set("summary")
        self.method_var.set("z")
        for g, (n, mean, sd) in ((self.g1, (40, 72.4, 8.2)), (self.g2, (45, 76.1, 9.1))):
            self._set(g["ents"]["n"], str(n))
            self._set(g["ents"]["mean"], str(mean))
            self._set(g["sd"], str(sd))
        self._refresh_mode()
        self.status.set("Example loaded — press Calculate (F5).")

    def load_csv(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("CSV / text", "*.csv *.txt *.tsv"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                sample = f.read(4096)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
                except csv.Error:
                    dialect = csv.excel
                cols: tuple[list[float], list[float]] = ([], [])
                for row in csv.reader(f, dialect):
                    for idx in (0, 1):
                        if idx < len(row):
                            try:
                                cols[idx].append(float(normalize(row[idx]).replace(",", ".")))
                            except ValueError:
                                pass  # header, blank or text cell
        except OSError as exc:
            messagebox.showerror("File error", str(exc))
            return
        if not cols[0] or not cols[1]:
            messagebox.showerror("CSV error", "Need two numeric columns (group 1 and group 2).")
            return
        for g, values in zip((self.g1, self.g2), cols):
            g["text"].delete("1.0", "end")
            g["text"].insert("1.0", "\n".join(repr(v) for v in values))
        self.source_var.set("raw")
        self._refresh_mode()
        self.status.set(f"Loaded {len(cols[0])} + {len(cols[1])} values from {path}")

    def copy_summary(self) -> None:
        if self.last is None:
            self.status.set("Nothing to copy yet — run an analysis first.")
            return
        self.clipboard_clear()
        self.clipboard_append(format_summary(self.last))
        self.status.set("Summary copied to clipboard.")

    def save_plot(self) -> None:
        if self.last is None:
            messagebox.showinfo("Save plot", "Run an analysis first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=[("PNG", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")])
        if not path:
            return
        self.fig.savefig(path, dpi=200, facecolor=self.fig.get_facecolor())
        self.status.set(f"Plot saved → {path}")

    def show_help(self) -> None:
        messagebox.showinfo("Formulas & notes", HELP_TEXT)


def main() -> None:
    if sys.platform == "win32":  # crisp text on high-DPI Windows displays
        try:
            from ctypes import windll

            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    App().mainloop()


if __name__ == "__main__":
    main()
