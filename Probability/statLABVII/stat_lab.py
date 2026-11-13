#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STAT LAB  -  Engineering Statistics & Probability Workbench
============================================================
A desktop (tkinter) tool for descriptive statistics, frequency analysis,
normality / outlier diagnostics, distribution fitting, hypothesis tests,
correlation / regression and a probability calculator.

Input   : CSV / TSV / TXT / DAT / XLSX / XLS / JSON files, or pasted numbers.
Requires: Python 3.9+, numpy, scipy, pandas, matplotlib   (openpyxl for .xlsx)
          pip install numpy scipy pandas matplotlib openpyxl
Run     : python stat_lab.py [optional_data_file]
"""
from __future__ import annotations

import csv
import io
import json
import math
import os
import re
import sys
import traceback
import warnings
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

try:
    import numpy as np
    import pandas as pd
    from scipy import stats
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    import tkinter.font as tkfont
except ImportError as _e:  # pragma: no cover
    sys.stderr.write(
        f"Missing dependency: {_e}\n"
        "Install with:  pip install numpy scipy pandas matplotlib openpyxl\n"
        "(tkinter ships with Python; on Debian/Ubuntu: sudo apt install python3-tk)\n")
    sys.exit(1)

APP_NAME = "STAT LAB"
APP_VERSION = "1.0"

# ----------------------------------------------------------------------------
# Theme  (dark / monochrome / phosphor green + cyan)
# ----------------------------------------------------------------------------
BG = "#0a0e0d"
PANEL = "#10171a"
PANEL2 = "#151f23"
BORDER = "#22313a"
FG = "#c9d6d2"
DIM = "#667a76"
ACCENT = "#39ff9c"
CYAN = "#2fd9ff"
WARN = "#ffb454"
ERR = "#ff5c6c"
SEL = "#16423a"

SIG_DIGITS = 6  # global display precision (significant digits)


# ----------------------------------------------------------------------------
# Number formatting
# ----------------------------------------------------------------------------
def fmt(v, sig: Optional[int] = None) -> str:
    """Format any value for display using `sig` significant digits."""
    sig = SIG_DIGITS if sig is None else sig
    if v is None:
        return "-"
    if isinstance(v, str):
        return v
    if isinstance(v, (bool, np.bool_)):
        return str(bool(v))
    if isinstance(v, (int, np.integer)):
        return f"{int(v):d}"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    if math.isnan(v):
        return "-"
    if math.isinf(v):
        return "inf" if v > 0 else "-inf"
    if v == 0:
        return "0"
    if v == int(v) and abs(v) < 1e15:
        return str(int(v))
    a = abs(v)
    if 1e-4 <= a < 1e12:
        return np.format_float_positional(v, precision=sig, unique=False,
                                          fractional=False, trim="-")
    return f"{v:.{max(sig - 1, 0)}e}"


def _peq(p) -> str:
    """'= 0.0123' or '< 1e-12' (so that text reads 'p = 0.0123' / 'p < 1e-12')."""
    t = fmt_p(p)
    return t if t.startswith("<") else "= " + t


def fmt_p(p) -> str:
    """p-values: never display as exactly 0."""
    try:
        p = float(p)
    except (TypeError, ValueError):
        return "-"
    if math.isnan(p):
        return "-"
    if p < 1e-12:
        return "< 1e-12"
    return fmt(p)


# ----------------------------------------------------------------------------
# Data loading / parsing
# ----------------------------------------------------------------------------
def _is_num(v, decimal: str = "auto") -> bool:
    if v is None:
        return False
    if isinstance(v, (bool, np.bool_)):
        return False
    if isinstance(v, (int, float, np.integer, np.floating)):
        return not (isinstance(v, float) and math.isnan(v))
    s = str(v).strip()
    if s == "":
        return False
    if decimal != ",":
        try:
            float(s)
            return True
        except ValueError:
            pass
    if decimal != ".":
        try:
            float(s.replace(",", "."))
            return True
        except ValueError:
            pass
    return False


def _unique_names(names: Sequence) -> List[str]:
    out, seen = [], {}
    for i, n in enumerate(names):
        n = str(n).strip() if n is not None and str(n).strip().lower() != "nan" else ""
        if not n:
            n = f"col{i + 1}"
        if n in seen:
            seen[n] += 1
            n = f"{n}_{seen[n]}"
        else:
            seen[n] = 0
        out.append(n)
    return out


def _split_rows(lines: List[str], decimal: str) -> List[List[str]]:
    """Detect the delimiter and split lines into fields."""
    sample = lines[:60]
    seps = [";", "\t", "|"]
    if decimal != ",":
        seps.append(",")
    for sep in seps:
        rows = list(csv.reader(sample, delimiter=sep))
        counts = {len(r) for r in rows}
        if len(counts) == 1 and next(iter(counts)) > 1:
            return [[c.strip() for c in r] for r in csv.reader(lines, delimiter=sep)]
    ws = [ln.split() for ln in sample]
    counts = {len(r) for r in ws}
    if len(counts) == 1 and next(iter(counts)) > 1:
        return [ln.split() for ln in lines]
    # try "mostly consistent" delimiters (ragged tables)
    for sep in seps:
        if all(sep in ln for ln in sample):
            return [[c.strip() for c in r] for r in csv.reader(lines, delimiter=sep)]
    return [[ln.strip()] for ln in lines]


def _raw_frame_from_text(text: str, decimal: str) -> pd.DataFrame:
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        raise ValueError("No data found (empty input).")
    if len(lines) == 1:  # a single line of numbers
        ln = lines[0].strip()
        if ";" in ln:
            toks = [t.strip() for t in ln.split(";")]
        elif decimal == ",":
            toks = ln.split()
        else:
            toks = [t for t in re.split(r"[,\s]+", ln) if t]
        return pd.DataFrame({0: toks}, dtype=object)
    rows = _split_rows(lines, decimal)
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    return pd.DataFrame(rows, dtype=object)


def _apply_header(raw: pd.DataFrame, header_mode: str, decimal: str) -> pd.DataFrame:
    has_header = False
    if raw.shape[0] >= 2:
        first = list(raw.iloc[0])
        if header_mode == "yes":
            has_header = True
        elif header_mode == "auto":
            has_header = not any(_is_num(v, decimal) for v in first)
    if has_header:
        names = _unique_names(list(raw.iloc[0]))
        df = raw.iloc[1:].reset_index(drop=True)
        df.columns = names
    else:
        df = raw.copy()
        df.columns = [f"col{i + 1}" if raw.shape[1] > 1 else "data" for i in range(raw.shape[1])]
    return df


def _coerce_numeric(df: pd.DataFrame, decimal: str) -> Tuple[pd.DataFrame, List[str]]:
    """Keep numeric columns (float64, NaN = missing). Return (frame, ignored_columns)."""
    cols, ignored = {}, []
    for c in df.columns:
        s = df[c]

        def clean_cell(v):
            if v is None:
                return ""
            if isinstance(v, float) and math.isnan(v):
                return ""
            return str(v).strip()

        t = s.map(clean_cell)
        non_empty = t != ""
        if non_empty.sum() == 0:
            ignored.append(c)
            continue
        base = t.where(non_empty, np.nan)
        num_dot = pd.to_numeric(base, errors="coerce")
        num_com = pd.to_numeric(base.str.replace(",", ".", regex=False), errors="coerce")
        share_dot = float(num_dot[non_empty].notna().mean())
        share_com = float(num_com[non_empty].notna().mean())
        if decimal == ".":
            num, share = num_dot, share_dot
        elif decimal == ",":
            num, share = num_com, share_com
        else:
            num, share = (num_dot, share_dot) if share_dot >= share_com else (num_com, share_com)
        if share < 0.5:
            ignored.append(c)
            continue
        arr = num.astype("float64").replace([np.inf, -np.inf], np.nan)
        cols[c] = arr
    if not cols:
        raise ValueError("No numeric column found in the data.")
    return pd.DataFrame(cols), ignored


def frame_from_text(text: str, header_mode: str = "auto", decimal: str = "auto"):
    raw = _raw_frame_from_text(text, decimal)
    return _coerce_numeric(_apply_header(raw, header_mode, decimal), decimal)


def excel_sheets(path: str) -> List[str]:
    try:
        return list(pd.ExcelFile(path).sheet_names)
    except Exception:
        return []


def load_file(path: str, header_mode: str = "auto", decimal: str = "auto",
              sheet: Optional[str] = None):
    """Return (numeric DataFrame, ignored_columns)."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm", ".xls", ".ods"):
        raw = pd.read_excel(path, sheet_name=sheet if sheet else 0, header=None, dtype=object)
        raw = raw.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)
        raw.columns = range(raw.shape[1])
        return _coerce_numeric(_apply_header(raw, header_mode, decimal), decimal)
    if ext == ".json":
        with open(path, "r", encoding="utf-8-sig") as f:
            obj = json.load(f)
        if isinstance(obj, list) and obj and not isinstance(obj[0], (dict, list)):
            df = pd.DataFrame({"data": obj})
        elif isinstance(obj, dict) and obj and all(isinstance(v, list) for v in obj.values()):
            df = pd.DataFrame({k: pd.Series(v) for k, v in obj.items()})
        else:
            df = pd.json_normalize(obj)
        df = df.astype(object)
        return _coerce_numeric(df, decimal)
    for enc in ("utf-8-sig", "utf-16", "cp1256", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                text = f.read()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        raise ValueError("Cannot decode the file.")
    return frame_from_text(text, header_mode, decimal)


# ----------------------------------------------------------------------------
# Statistics engine (pure functions - no GUI)
# ----------------------------------------------------------------------------
QUANTILE_METHODS = ["linear", "weibull", "hazen", "median_unbiased", "normal_unbiased",
                    "lower", "higher", "midpoint", "nearest"]


def clean(a) -> np.ndarray:
    a = np.asarray(a, dtype=float).ravel()
    return a[np.isfinite(a)]


def _quiet(fn: Callable, *a, default=float("nan"), **k):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with np.errstate(all="ignore"):
                return fn(*a, **k)
    except Exception:
        return default


def quartiles_halves(x: np.ndarray, include_median: bool):
    xs = np.sort(x)
    n = len(xs)
    if n < 2:
        return float("nan"), float("nan")
    mid = n // 2
    if n % 2 == 0:
        lo, hi = xs[:mid], xs[mid:]
    elif include_median:
        lo, hi = xs[:mid + 1], xs[mid:]
    else:
        lo, hi = xs[:mid], xs[mid + 1:]
    return float(np.median(lo)), float(np.median(hi))


def describe(x, n_missing: int = 0, conf: float = 0.95, trim: float = 0.10,
             qmethod: str = "linear"):
    """Return rows (group, statistic, value, note)."""
    x = clean(x)
    n = len(x)
    rows: List[Tuple[str, str, object, str]] = []

    def add(g, name, val, note=""):
        rows.append((g, name, val, note))

    if n == 0:
        return rows
    alpha = 1 - conf
    mean = math.fsum(x) / n
    med = float(np.median(x))
    sd_s = float(np.std(x, ddof=1)) if n > 1 else float("nan")
    sd_p = float(np.std(x, ddof=0))
    var_s = sd_s ** 2 if n > 1 else float("nan")
    var_p = sd_p ** 2
    q = lambda p: float(np.quantile(x, p, method=qmethod))
    q1, q3 = q(0.25), q(0.75)

    add("SIZE", "n (valid observations)", n)
    add("SIZE", "Missing / non-numeric", int(n_missing))
    add("SIZE", "Sum  (Σx)", math.fsum(x))
    add("SIZE", "Sum of squares  (Σx²)", math.fsum(x * x))
    add("SIZE", "Sum of squared deviations  (Sxx)", math.fsum((x - mean) ** 2))

    add("LOCATION", "Mean  (x̄)", mean)
    add("LOCATION", "Median", med)
    vals, cnts = np.unique(x, return_counts=True)
    if cnts.max() == 1:
        add("LOCATION", "Mode", "none", "all values unique")
    else:
        m = vals[cnts == cnts.max()]
        s = ", ".join(fmt(v) for v in m[:5]) + (" ..." if len(m) > 5 else "")
        add("LOCATION", "Mode", s, f"frequency = {int(cnts.max())}" +
            (f", {len(m)} modes" if len(m) > 1 else ""))
    add("LOCATION", f"Trimmed mean ({trim * 100:g}% each tail)",
        _quiet(stats.trim_mean, x, trim), "robust mean")
    pos = bool(np.all(x > 0))
    add("LOCATION", "Geometric mean", float(np.exp(np.mean(np.log(x)))) if pos else float("nan"),
        "" if pos else "requires all x > 0")
    add("LOCATION", "Harmonic mean", float(n / np.sum(1.0 / x)) if pos else float("nan"),
        "" if pos else "requires all x > 0")
    add("LOCATION", "Midrange", (float(x.min()) + float(x.max())) / 2)

    add("SPREAD", "Minimum", float(x.min()))
    add("SPREAD", "Maximum", float(x.max()))
    add("SPREAD", "Range", float(x.max() - x.min()))
    add("SPREAD", "Variance  (sample, n−1)  s²", var_s)
    add("SPREAD", "Variance  (population, n)  σ²", var_p)
    add("SPREAD", "Std deviation  (sample)  s", sd_s)
    add("SPREAD", "Std deviation  (population)  σ", sd_p)
    add("SPREAD", "Standard error of mean  (s/√n)", sd_s / math.sqrt(n) if n > 1 else float("nan"))
    add("SPREAD", "Coefficient of variation  (s/|x̄|, %)",
        sd_s / abs(mean) * 100 if (n > 1 and mean != 0) else float("nan"))
    add("SPREAD", "Mean absolute deviation (about mean)", float(np.mean(np.abs(x - mean))))
    mad = float(np.median(np.abs(x - med)))
    add("SPREAD", "Median absolute deviation (MAD)", mad)
    add("SPREAD", "Scaled MAD  (1.4826·MAD)", 1.4826 * mad, "robust σ estimate for normal data")
    add("SPREAD", "Interquartile range  (IQR)", q3 - q1, f"method: {qmethod}")

    add("QUANTILES", "Q1  (25th percentile)", q1, f"method: {qmethod}")
    add("QUANTILES", "Q2  (median)", med)
    add("QUANTILES", "Q3  (75th percentile)", q3, f"method: {qmethod}")
    h1, h3 = quartiles_halves(x, include_median=False)
    t1, t3 = quartiles_halves(x, include_median=True)
    add("QUANTILES", "Q1 / Q3  median-of-halves (median excluded)", f"{fmt(h1)}  /  {fmt(h3)}",
        "Moore-McCabe textbook rule")
    add("QUANTILES", "Q1 / Q3  Tukey hinges (median included)", f"{fmt(t1)}  /  {fmt(t3)}",
        "lower/upper hinge")
    for p in (1, 5, 10, 90, 95, 99):
        add("QUANTILES", f"P{p}  (percentile {p})", q(p / 100))

    add("SHAPE", "Skewness  g1  (population)", _quiet(stats.skew, x, bias=True))
    add("SHAPE", "Skewness  G1  (sample-adjusted)",
        _quiet(stats.skew, x, bias=False) if n >= 3 else float("nan"), "as in Excel SKEW()")
    add("SHAPE", "Excess kurtosis  g2  (population)", _quiet(stats.kurtosis, x, fisher=True, bias=True))
    add("SHAPE", "Excess kurtosis  G2  (sample-adjusted)",
        _quiet(stats.kurtosis, x, fisher=True, bias=False) if n >= 4 else float("nan"),
        "as in Excel KURT()")
    add("SHAPE", "Kurtosis  b2  (Pearson, normal = 3)",
        _quiet(stats.kurtosis, x, fisher=False, bias=True))
    add("SHAPE", "Pearson 2nd skewness  3(x̄ − median)/s",
        3 * (mean - med) / sd_s if (n > 1 and sd_s > 0) else float("nan"))
    add("SHAPE", "Bowley skewness  (Q3+Q1−2Q2)/(Q3−Q1)",
        (q3 + q1 - 2 * med) / (q3 - q1) if q3 != q1 else float("nan"))
    if n >= 3:
        ses = math.sqrt(6.0 * n * (n - 1) / ((n - 2) * (n + 1) * (n + 3)))
        add("SHAPE", "Std error of skewness", ses)
        if n >= 4:
            add("SHAPE", "Std error of kurtosis", 2 * ses * math.sqrt((n * n - 1) / ((n - 3) * (n + 5))))

    if n > 1:
        tcrit = float(stats.t.ppf(1 - alpha / 2, n - 1))
        half = tcrit * sd_s / math.sqrt(n)
        c = f"{conf * 100:g}%"
        add("CONFIDENCE", f"t critical  t(α/2, n−1)  [{c}]", tcrit)
        add("CONFIDENCE", f"Margin of error for mean [{c}]", half)
        add("CONFIDENCE", f"CI for mean (t) [{c}]", f"({fmt(mean - half)} ,  {fmt(mean + half)})")
        chi_lo = float(stats.chi2.ppf(alpha / 2, n - 1))
        chi_hi = float(stats.chi2.ppf(1 - alpha / 2, n - 1))
        v_lo, v_hi = (n - 1) * var_s / chi_hi, (n - 1) * var_s / chi_lo
        add("CONFIDENCE", f"CI for variance σ² (χ²) [{c}]", f"({fmt(v_lo)} ,  {fmt(v_hi)})")
        add("CONFIDENCE", f"CI for std deviation σ (χ²) [{c}]",
            f"({fmt(math.sqrt(v_lo))} ,  {fmt(math.sqrt(v_hi))})")
        pih = tcrit * sd_s * math.sqrt(1 + 1 / n)
        add("CONFIDENCE", f"Prediction interval, 1 new obs. [{c}]", f"({fmt(mean - pih)} ,  {fmt(mean + pih)})",
            "x̄ ± t·s·√(1+1/n)")
        if n > 2:
            kt = tolerance_k(n, 0.95, conf)
            add("CONFIDENCE", f"Tolerance interval, 95% of population [{c}]",
                f"({fmt(mean - kt * sd_s)} ,  {fmt(mean + kt * sd_s)})", f"k = {fmt(kt)} (Howe), normal data")

    iqr = q3 - q1
    lo15, hi15, lo3, hi3 = q1 - 1.5 * iqr, q3 + 1.5 * iqr, q1 - 3 * iqr, q3 + 3 * iqr
    add("OUTLIERS", "Tukey fences  (1.5×IQR)", f"[{fmt(lo15)} ,  {fmt(hi15)}]")
    add("OUTLIERS", "Points outside 1.5×IQR fences", int(np.sum((x < lo15) | (x > hi15))), "mild + extreme")
    add("OUTLIERS", "Points outside 3×IQR fences", int(np.sum((x < lo3) | (x > hi3))), "extreme")
    if n > 1 and sd_s > 0:
        add("OUTLIERS", "Points with |z| > 3", int(np.sum(np.abs((x - mean) / sd_s) > 3)))
    return rows


def bin_edges(x, method: str = "sturges", param: Optional[float] = None) -> np.ndarray:
    """Histogram class boundaries for a given rule (shared by table and plots)."""
    x = clean(x)
    if method == "discrete (unique values)":
        if np.all(x == np.round(x)):
            return np.arange(np.floor(x.min()) - 0.5, np.ceil(x.max()) + 1.5, 1.0)
        method = "auto"
    if method == "number of bins":
        k = int(param) if param else 10
        if k < 1:
            raise ValueError("Number of bins must be ≥ 1.")
        return np.histogram_bin_edges(x, bins=k)
    if method == "class width":
        w = float(param) if param else 0
        if w <= 0:
            raise ValueError("Class width must be > 0.")
        start = math.floor(x.min() / w) * w
        edges = np.arange(start, x.max() + w * 1.0000001, w)
        if edges[-1] <= x.max():
            edges = np.append(edges, edges[-1] + w)
        return edges
    return np.histogram_bin_edges(x, bins=method)


def frequency_table(x, method: str = "sturges", param: Optional[float] = None):
    """Return (columns, rows, info)."""
    x = clean(x)
    n = len(x)
    if n == 0:
        raise ValueError("No data.")
    if method == "discrete (unique values)":
        vals, cnts = np.unique(x, return_counts=True)
        cum = np.cumsum(cnts)
        cols = ["Value", "Frequency", "Rel. freq", "Cum. freq", "Cum. rel. freq", "Percent"]
        rows = [(fmt(v), int(c), c / n, int(cu), cu / n, c / n * 100)
                for v, c, cu in zip(vals, cnts, cum)]
        return cols, rows, f"{len(vals)} distinct values, n = {n}"
    edges = bin_edges(x, method, param)
    counts, edges = np.histogram(x, bins=edges)
    cum = np.cumsum(counts)
    widths = np.diff(edges)
    cols = ["Class", "Midpoint", "Frequency", "Rel. freq", "Cum. freq", "Cum. rel. freq", "Density"]
    rows = []
    for i, c in enumerate(counts):
        lo, hi = edges[i], edges[i + 1]
        close = "]" if i == len(counts) - 1 else ")"
        rows.append((f"[{fmt(lo)} , {fmt(hi)}{close}", (lo + hi) / 2, int(c), c / n,
                     int(cum[i]), cum[i] / n, c / n / widths[i]))
    return cols, rows, (f"{len(counts)} classes, class width = {fmt(widths[0])}, n = {n}"
                        f"  (classes are half-open [a,b); the last is closed)")


def stem_and_leaf(x) -> str:
    x = clean(x)
    n = len(x)
    if n == 0:
        return "No data."
    xs = np.sort(x)
    if xs[0] == xs[-1]:
        return f"All {n} values are equal to {fmt(xs[0])}."
    unit = None
    for k in range(-9, 10):
        u = 10.0 ** k
        s_lo = math.trunc(round(xs[0] / u, 9) / 10)
        s_hi = math.trunc(round(xs[-1] / u, 9) / 10)
        if abs(s_hi - s_lo) + 1 <= 25:
            unit = u
            break
    if unit is None:
        return "Range too large for a stem-and-leaf display."
    q = [int(math.trunc(round(v / unit, 9))) for v in xs]
    neg = [v < 0 or (v == 0 and xs[i] < 0) for i, v in enumerate(q)]
    stems = {}
    for qi, ng in zip(q, neg):
        a = abs(qi)
        stems.setdefault((ng, a // 10), []).append(a % 10)
    for sign in (False, True):
        present = [st for (ng, st) in stems if ng == sign]
        if present:
            for st in range(min(present), max(present) + 1):
                stems.setdefault((sign, st), [])
    split = len(stems) < 8
    keys = sorted(stems, key=lambda k: (not k[0], -k[1] if k[0] else k[1]))
    lines = []
    for ng, st in keys:
        leaves = sorted(stems[(ng, st)])
        label = ("-" if ng else " ") + str(st)
        if split:
            lo = "".join(map(str, [l for l in leaves if l < 5]))
            hi = "".join(map(str, [l for l in leaves if l >= 5]))
            lines.append((label, "(0-4)", lo))
            lines.append((label, "(5-9)", hi))
        else:
            lines.append((label, "", "".join(map(str, leaves))))
    w = max(len(l[0]) for l in lines)
    out = [f"STEM-AND-LEAF  (n = {n},  leaf unit = {fmt(unit)})", ""]
    for lab, tag, lv in lines:
        out.append(f"{lab.rjust(w)} {tag:<5}| {lv}" if split else f"{lab.rjust(w)} | {lv}")
    k0 = next(k for k in keys if stems[k])
    ex_stem, ex_leaf = k0[1], sorted(stems[k0])[0]
    ex_val = (-1 if k0[0] else 1) * (ex_stem * 10 + ex_leaf) * unit
    out += ["", f"Key:  {'-' if k0[0] else ''}{ex_stem} | {ex_leaf}  =  {fmt(ex_val)}"]
    return "\n".join(out)


# ----- normality / outliers ---------------------------------------------------
def lilliefors(x: np.ndarray, nsim: int = 2000, seed: int = 12345):
    n = len(x)
    sd = x.std(ddof=1)
    if n < 4 or sd == 0:
        return float("nan"), float("nan")
    idx = np.arange(1, n + 1)

    def ks(z_sorted):
        cdf = stats.norm.cdf(z_sorted)
        return np.maximum((idx / n - cdf).max(axis=-1), (cdf - (idx - 1) / n).max(axis=-1))

    z = np.sort((x - x.mean()) / sd)
    d = float(ks(z))
    rng = np.random.default_rng(seed)
    nsim = max(200, min(nsim, int(2_000_000 / n)))
    batch = max(1, min(nsim, int(1_000_000 / n)))
    done = cnt = 0
    while done < nsim:
        b = min(batch, nsim - done)
        s = rng.standard_normal((b, n))
        s = (s - s.mean(axis=1, keepdims=True)) / s.std(axis=1, ddof=1, keepdims=True)
        s.sort(axis=1)
        cnt += int(np.sum(ks(s) >= d))
        done += b
    return d, (cnt + 1) / (nsim + 1)


def anderson_darling(x: np.ndarray):
    n = len(x)
    if n < 8 or x.std(ddof=1) == 0:
        return float("nan"), float("nan"), float("nan")
    z = np.sort((x - x.mean()) / x.std(ddof=1))
    i = np.arange(1, n + 1)
    a2 = float(-n - np.sum((2 * i - 1) * (stats.norm.logcdf(z) + stats.norm.logsf(z[::-1]))) / n)
    a2s = a2 * (1 + 0.75 / n + 2.25 / n ** 2)
    if a2s >= 0.6:
        p = math.exp(1.2937 - 5.709 * a2s + 0.0186 * a2s ** 2)
    elif a2s >= 0.34:
        p = math.exp(0.9177 - 4.279 * a2s - 1.38 * a2s ** 2)
    elif a2s >= 0.2:
        p = 1 - math.exp(-8.318 + 42.796 * a2s - 59.938 * a2s ** 2)
    else:
        p = 1 - math.exp(-13.436 + 101.14 * a2s - 223.73 * a2s ** 2)
    return a2, a2s, min(max(p, 0.0), 1.0)


def normality_tests(x, alpha: float = 0.05):
    """Return list of (test, statistic_text, p, decision, note)."""
    x = clean(x)
    n = len(x)
    out = []

    def dec(p):
        if p is None or (isinstance(p, float) and math.isnan(p)):
            return "n/a"
        return "Reject normality" if p < alpha else "Do not reject"

    if n < 3 or np.ptp(x) == 0:
        return out
    r = _quiet(stats.shapiro, x, default=None)
    if r is not None:
        out.append(("Shapiro-Wilk", f"W = {fmt(r.statistic)}", float(r.pvalue), dec(float(r.pvalue)),
                    "best power for small/medium n" + ("; p approximate for n > 5000" if n > 5000 else "")))
    if n >= 8:
        r = _quiet(stats.normaltest, x, default=None)
        if r is not None:
            out.append(("D'Agostino-Pearson K²", f"K² = {fmt(r.statistic)}", float(r.pvalue),
                        dec(float(r.pvalue)), "skewness + kurtosis omnibus; needs n ≥ 8"))
        a2, a2s, pad = anderson_darling(x)
        if not math.isnan(pad):
            out.append(("Anderson-Darling", f"A² = {fmt(a2)}  (A*² = {fmt(a2s)})", pad, dec(pad),
                        "tail-sensitive; Stephens p-value approximation"))
    r = _quiet(stats.jarque_bera, x, default=None)
    if r is not None:
        out.append(("Jarque-Bera", f"JB = {fmt(r.statistic)}", float(r.pvalue), dec(float(r.pvalue)),
                    "asymptotic; reliable for large n only"))
    d, p = lilliefors(x)
    if not math.isnan(p):
        out.append(("Lilliefors (KS, estimated μ,σ)", f"D = {fmt(d)}", p, dec(p),
                    "Monte-Carlo p-value"))
    return out


def outlier_report(x, rows, alpha: float = 0.05, qmethod: str = "linear"):
    """Return dict of method -> (description, [(row, value), ...])."""
    x = np.asarray(x, float)
    rows = np.asarray(rows)
    n = len(x)
    res = {}
    if n < 3:
        return res
    q1, q3 = np.quantile(x, [0.25, 0.75], method=qmethod)
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    elo, ehi = q1 - 3 * iqr, q3 + 3 * iqr
    m = (x < lo) | (x > hi)
    res["Tukey 1.5×IQR"] = (f"fences [{fmt(lo)}, {fmt(hi)}]", list(zip(rows[m], x[m])))
    m = (x < elo) | (x > ehi)
    res["Tukey 3×IQR (extreme)"] = (f"fences [{fmt(elo)}, {fmt(ehi)}]", list(zip(rows[m], x[m])))
    sd = x.std(ddof=1)
    if sd > 0:
        z = (x - x.mean()) / sd
        m = np.abs(z) > 3
        res["z-score |z| > 3"] = (f"mean = {fmt(x.mean())}, s = {fmt(sd)}", list(zip(rows[m], x[m])))
    med = np.median(x)
    mad = np.median(np.abs(x - med))
    if mad > 0:
        mz = 0.6745 * (x - med) / mad
        m = np.abs(mz) > 3.5
        res["Modified z |M| > 3.5 (Iglewicz-Hoaglin)"] = (
            f"median = {fmt(med)}, MAD = {fmt(mad)}", list(zip(rows[m], x[m])))
    if sd > 0:
        i = int(np.argmax(np.abs(x - x.mean())))
        g = abs(x[i] - x.mean()) / sd
        t = float(stats.t.ppf(1 - alpha / (2 * n), n - 2))
        gcrit = (n - 1) / math.sqrt(n) * math.sqrt(t * t / (n - 2 + t * t))
        flag = g > gcrit
        res[f"Grubbs test (two-sided, α = {alpha:g})"] = (
            f"G = {fmt(g)},  G_crit = {fmt(gcrit)}  ->  "
            + ("OUTLIER at the most extreme point" if flag else "no single outlier detected"),
            [(rows[i], x[i])] if flag else [])
    return res


# ----- distribution fitting ---------------------------------------------------
def _fit_candidates():
    return [
        ("Normal", stats.norm, {}, lambda x: True,
         lambda p: f"μ = {fmt(p[0])}, σ = {fmt(p[1])}"),
        ("Lognormal", stats.lognorm, {"floc": 0}, lambda x: x.min() > 0,
         lambda p: f"μ_ln = {fmt(math.log(p[2]))}, σ_ln = {fmt(p[0])}"),
        ("Exponential", stats.expon, {"floc": 0}, lambda x: x.min() >= 0,
         lambda p: f"λ = {fmt(1 / p[1])}  (mean = {fmt(p[1])})"),
        ("Gamma", stats.gamma, {"floc": 0}, lambda x: x.min() > 0,
         lambda p: f"shape k = {fmt(p[0])}, rate λ = {fmt(1 / p[2])}"),
        ("Weibull", stats.weibull_min, {"floc": 0}, lambda x: x.min() > 0,
         lambda p: f"shape β = {fmt(p[0])}, scale η = {fmt(p[2])}"),
        ("Rayleigh", stats.rayleigh, {"floc": 0}, lambda x: x.min() >= 0,
         lambda p: f"σ = {fmt(p[1])}"),
        ("Uniform", stats.uniform, {}, lambda x: True,
         lambda p: f"a = {fmt(p[0])}, b = {fmt(p[0] + p[1])}"),
        ("Logistic", stats.logistic, {}, lambda x: True,
         lambda p: f"μ = {fmt(p[0])}, s = {fmt(p[1])}"),
        ("Laplace", stats.laplace, {}, lambda x: True,
         lambda p: f"μ = {fmt(p[0])}, b = {fmt(p[1])}"),
        ("Gumbel (max)", stats.gumbel_r, {}, lambda x: True,
         lambda p: f"μ = {fmt(p[0])}, β = {fmt(p[1])}"),
    ]


def fit_distributions(x):
    x = clean(x)
    n = len(x)
    if n < 5 or np.ptp(x) == 0:
        raise ValueError("Need at least 5 non-constant observations to fit distributions.")
    res = []
    for name, dist, kw, ok, pretty in _fit_candidates():
        if not ok(x):
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                with np.errstate(all="ignore"):
                    params = dist.fit(x, **kw)
                    ll = float(np.sum(dist.logpdf(x, *params)))
                    if not np.isfinite(ll):
                        continue
                    k = len(params) - len(kw)
                    ks = stats.kstest(x, dist.cdf, args=params)
            res.append(dict(name=name, dist=dist, params=params, pretty=pretty(params), ll=ll, k=k,
                            aic=2 * k - 2 * ll, bic=k * math.log(n) - 2 * ll,
                            ks=float(ks.statistic), ksp=float(ks.pvalue)))
        except Exception:
            continue
    res.sort(key=lambda r: r["aic"])
    if res:
        best = res[0]["aic"]
        for r in res:
            r["daic"] = r["aic"] - best
    return res


# ----- hypothesis tests -------------------------------------------------------
ALT_LABELS = {"two-sided": "two-sided", "less": "less", "greater": "greater"}


def _p_from_cdf(cdf_val: float, sf_val: float, alt: str) -> float:
    if alt == "less":
        return cdf_val
    if alt == "greater":
        return sf_val
    return min(1.0, 2 * min(cdf_val, sf_val))


def _decision(p: float, alpha: float) -> str:
    pt = fmt_p(p)
    lead = "p " if pt.startswith("<") else "p = "
    return (f"{lead}{pt} {'<' if p < alpha else '≥'} α = {alpha:g}  ->  "
            + ("REJECT H0" if p < alpha else "FAIL TO REJECT H0"))


def _h_lines(h0: str, alt: str, par: str, v0: str) -> List[str]:
    sym = {"two-sided": "≠", "less": "<", "greater": ">"}[alt]
    return [f"H0 : {par} = {v0}", f"H1 : {par} {sym} {v0}   ({alt})"]


def run_test(name: str, a: np.ndarray, b: Optional[np.ndarray], alpha: float, alt: str,
             mu0: float = 0.0, sigma0: float = 1.0, sigma2: float = 1.0,
             groups: Optional[List[np.ndarray]] = None,
             pair_ab: Optional[Tuple[np.ndarray, np.ndarray]] = None,
             names: Optional[List[str]] = None) -> str:
    """Run a named hypothesis test and return a formatted report."""
    if name in EXTRA_TESTS:
        return extra_test(name, a, b, alpha, alt, mu0, groups or [], names or [])
    L: List[str] = [f"TEST: {name}", "=" * (6 + len(name))]
    conf = 1 - alpha

    def ci_t(mean, se, df):
        if alt == "two-sided":
            t = stats.t.ppf(1 - alpha / 2, df)
            return f"{conf * 100:g}% CI: ({fmt(mean - t * se)} , {fmt(mean + t * se)})"
        t = stats.t.ppf(1 - alpha, df)
        return (f"{conf * 100:g}% one-sided CI: ({fmt(mean - t * se)} , ∞)" if alt == "greater"
                else f"{conf * 100:g}% one-sided CI: (-∞ , {fmt(mean + t * se)})")

    def crit_t(df):
        if alt == "two-sided":
            c = stats.t.ppf(1 - alpha / 2, df)
            return f"critical values: ±{fmt(c)}   (reject if |t| > {fmt(c)})"
        c = stats.t.ppf(1 - alpha, df)
        return (f"critical value: {fmt(c)}   (reject if t > {fmt(c)})" if alt == "greater"
                else f"critical value: {fmt(-c)}   (reject if t < {fmt(-c)})")

    if name == "One-sample t-test":
        x = clean(a)
        n = len(x)
        if n < 2:
            raise ValueError("Need n ≥ 2.")
        m, s = x.mean(), x.std(ddof=1)
        se = s / math.sqrt(n)
        t = (m - mu0) / se
        df = n - 1
        p = _p_from_cdf(stats.t.cdf(t, df), stats.t.sf(t, df), alt)
        L += _h_lines("", alt, "μ", fmt(mu0))
        L += ["", f"n = {n},  x̄ = {fmt(m)},  s = {fmt(s)},  SE = {fmt(se)}",
              f"t = (x̄ − μ0)/(s/√n) = {fmt(t)},   df = {df}", crit_t(df),
              ci_t(m, se, df), f"Cohen's d = {fmt((m - mu0) / s)}", "", _decision(p, alpha)]
    elif name == "One-sample z-test (σ known)":
        x = clean(a)
        n = len(x)
        if sigma0 <= 0:
            raise ValueError("σ must be > 0.")
        m = x.mean()
        se = sigma0 / math.sqrt(n)
        z = (m - mu0) / se
        p = _p_from_cdf(stats.norm.cdf(z), stats.norm.sf(z), alt)
        zc = stats.norm.ppf(1 - alpha / 2) if alt == "two-sided" else stats.norm.ppf(1 - alpha)
        L += _h_lines("", alt, "μ", fmt(mu0))
        L += ["", f"n = {n},  x̄ = {fmt(m)},  known σ = {fmt(sigma0)},  SE = {fmt(se)}",
              f"z = (x̄ − μ0)/(σ/√n) = {fmt(z)}",
              f"critical value: {'±' if alt == 'two-sided' else ''}{fmt(zc)}"
              if alt != "less" else f"critical value: {fmt(-zc)}"]
        if alt == "two-sided":
            L.append(f"{conf * 100:g}% CI: ({fmt(m - zc * se)} , {fmt(m + zc * se)})")
        L += ["", _decision(p, alpha)]
    elif name == "Chi-square test for variance":
        x = clean(a)
        n = len(x)
        if n < 2 or sigma0 <= 0:
            raise ValueError("Need n ≥ 2 and σ0 > 0 (enter σ0 as the hypothesised std deviation).")
        s2 = x.var(ddof=1)
        chi = (n - 1) * s2 / sigma0 ** 2
        df = n - 1
        p = _p_from_cdf(stats.chi2.cdf(chi, df), stats.chi2.sf(chi, df), alt)
        L += _h_lines("", alt, "σ²", fmt(sigma0 ** 2))
        if alt == "two-sided":
            cl, ch = stats.chi2.ppf(alpha / 2, df), stats.chi2.ppf(1 - alpha / 2, df)
            L_crit = f"critical values: {fmt(cl)} and {fmt(ch)}"
            ci = f"{conf * 100:g}% CI for σ²: ({fmt((n - 1) * s2 / ch)} , {fmt((n - 1) * s2 / cl)})"
        elif alt == "greater":
            c = stats.chi2.ppf(1 - alpha, df)
            L_crit = f"critical value: {fmt(c)}   (reject if χ² > {fmt(c)})"
            ci = f"{conf * 100:g}% one-sided CI for σ²: ({fmt((n - 1) * s2 / c)} , ∞)"
        else:
            c = stats.chi2.ppf(alpha, df)
            L_crit = f"critical value: {fmt(c)}   (reject if χ² < {fmt(c)})"
            ci = f"{conf * 100:g}% one-sided CI for σ²: (0 , {fmt((n - 1) * s2 / c)})"
        L += ["", f"n = {n},  s² = {fmt(s2)},  s = {fmt(math.sqrt(s2))},  σ0² = {fmt(sigma0 ** 2)}",
              f"χ² = (n−1)s²/σ0² = {fmt(chi)},   df = {df}", L_crit, ci, "", _decision(p, alpha)]
    elif name in ("Two-sample t-test (Welch)", "Two-sample t-test (pooled)"):
        x, y = clean(a), clean(b)
        n1, n2 = len(x), len(y)
        if n1 < 2 or n2 < 2:
            raise ValueError("Each sample needs n ≥ 2.")
        m1, m2, v1, v2 = x.mean(), y.mean(), x.var(ddof=1), y.var(ddof=1)
        if name.endswith("(Welch)"):
            se = math.sqrt(v1 / n1 + v2 / n2)
            df = (v1 / n1 + v2 / n2) ** 2 / ((v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1))
            note = "unequal variances assumed (Welch-Satterthwaite df)"
        else:
            sp2 = ((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2)
            se = math.sqrt(sp2 * (1 / n1 + 1 / n2))
            df = n1 + n2 - 2
            note = f"equal variances assumed, pooled s_p = {fmt(math.sqrt(sp2))}"
        d = m1 - m2
        t = (d - mu0) / se
        p = _p_from_cdf(stats.t.cdf(t, df), stats.t.sf(t, df), alt)
        L += _h_lines("", alt, "μ_X − μ_Y", fmt(mu0))
        sp = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
        L += ["", note, f"X: n = {n1}, mean = {fmt(m1)}, s = {fmt(math.sqrt(v1))}",
              f"Y: n = {n2}, mean = {fmt(m2)}, s = {fmt(math.sqrt(v2))}",
              f"difference (x̄ − ȳ) = {fmt(d)},  SE = {fmt(se)}",
              f"t = {fmt(t)},   df = {fmt(df)}", crit_t(df), ci_t(d, se, df),
              f"Cohen's d = {fmt(d / sp)}", "", _decision(p, alpha)]
    elif name == "Two-sample z-test (σ known)":
        x, y = clean(a), clean(b)
        n1, n2 = len(x), len(y)
        s1, s2 = sigma0, sigma2
        if s1 <= 0 or s2 <= 0:
            raise ValueError("Both σ values must be > 0.")
        d = x.mean() - y.mean()
        se = math.sqrt(s1 ** 2 / n1 + s2 ** 2 / n2)
        z = (d - mu0) / se
        p = _p_from_cdf(stats.norm.cdf(z), stats.norm.sf(z), alt)
        zc = stats.norm.ppf(1 - alpha / 2) if alt == "two-sided" else stats.norm.ppf(1 - alpha)
        L += _h_lines("", alt, "μ_X − μ_Y", fmt(mu0))
        L += ["", f"X: n = {n1}, mean = {fmt(x.mean())}, σ_X = {fmt(s1)}",
              f"Y: n = {n2}, mean = {fmt(y.mean())}, σ_Y = {fmt(s2)}",
              f"difference = {fmt(d)},  SE = {fmt(se)}", f"z = {fmt(z)}"]
        if alt == "two-sided":
            L += [f"critical values: ±{fmt(zc)}",
                  f"{conf * 100:g}% CI: ({fmt(d - zc * se)} , {fmt(d + zc * se)})"]
        L += ["", _decision(p, alpha)]
    elif name == "Paired t-test":
        if pair_ab is None or len(pair_ab[0]) < 2:
            raise ValueError("Need ≥ 2 complete (X, Y) pairs.")
        x, y = pair_ab
        d = x - y
        n = len(d)
        m, s = d.mean(), d.std(ddof=1)
        se = s / math.sqrt(n)
        t = (m - mu0) / se if se > 0 else float("nan")
        df = n - 1
        p = _p_from_cdf(stats.t.cdf(t, df), stats.t.sf(t, df), alt)
        L += _h_lines("", alt, "μ_D (mean of X − Y)", fmt(mu0))
        L += ["", f"pairs n = {n},  mean difference = {fmt(m)},  s_D = {fmt(s)},  SE = {fmt(se)}",
              f"t = {fmt(t)},   df = {df}", crit_t(df), ci_t(m, se, df),
              f"Cohen's d_z = {fmt(m / s) if s > 0 else '-'}", "", _decision(p, alpha)]
    elif name == "F-test (equality of variances)":
        x, y = clean(a), clean(b)
        n1, n2 = len(x), len(y)
        if n1 < 2 or n2 < 2:
            raise ValueError("Each sample needs n ≥ 2.")
        v1, v2 = x.var(ddof=1), y.var(ddof=1)
        F = v1 / v2
        d1, d2 = n1 - 1, n2 - 1
        p = _p_from_cdf(stats.f.cdf(F, d1, d2), stats.f.sf(F, d1, d2), alt)
        L += _h_lines("", alt, "σ²_X / σ²_Y", "1")
        L += ["", f"s²_X = {fmt(v1)} (n = {n1}),  s²_Y = {fmt(v2)} (n = {n2})",
              f"F = s²_X / s²_Y = {fmt(F)},   df = ({d1}, {d2})"]
        if alt == "two-sided":
            fl, fh = stats.f.ppf(alpha / 2, d1, d2), stats.f.ppf(1 - alpha / 2, d1, d2)
            L += [f"critical values: {fmt(fl)} and {fmt(fh)}",
                  f"{conf * 100:g}% CI for σ²_X/σ²_Y: ({fmt(F / fh)} , {fmt(F / fl)})"]
        L += ["", _decision(p, alpha),
              "Note: the F-test is very sensitive to non-normality."]
    elif name == "Wilcoxon signed-rank (one-sample)":
        d = clean(a) - mu0
        if np.all(d == 0):
            raise ValueError("All differences are zero.")
        r = stats.wilcoxon(d, alternative=alt)
        L += [f"H0 : median of X = {fmt(mu0)}   (H1: {alt})", f"n = {len(d)} (zero differences are dropped)",
              f"W = {fmt(r.statistic)}", "", _decision(float(r.pvalue), alpha)]
    elif name == "Wilcoxon signed-rank (paired)":
        if pair_ab is None or len(pair_ab[0]) < 2:
            raise ValueError("Need ≥ 2 complete (X, Y) pairs.")
        d = pair_ab[0] - pair_ab[1] - mu0
        if np.all(d == 0):
            raise ValueError("All differences are zero.")
        r = stats.wilcoxon(d, alternative=alt)
        L += [f"H0 : median of (X − Y) = {fmt(mu0)}   (H1: {alt})", f"pairs n = {len(d)}",
              f"W = {fmt(r.statistic)}", "", _decision(float(r.pvalue), alpha)]
    elif name == "Mann-Whitney U (two independent samples)":
        x, y = clean(a), clean(b)
        r = stats.mannwhitneyu(x, y, alternative=alt)
        L += [f"n_X = {len(x)}, n_Y = {len(y)}", f"U = {fmt(r.statistic)}",
              f"rank-biserial r = {fmt(1 - 2 * r.statistic / (len(x) * len(y)))}", "",
              _decision(float(r.pvalue), alpha)]
    elif name in ("One-way ANOVA (all columns)", "Kruskal-Wallis (all columns)"):
        g = [clean(v) for v in (groups or []) if len(clean(v)) > 0]
        if len(g) < 2:
            raise ValueError("Need at least two columns with data.")
        if name.startswith("One-way"):
            r = stats.f_oneway(*g)
            allx = np.concatenate(g)
            gm = allx.mean()
            ssb = sum(len(v) * (v.mean() - gm) ** 2 for v in g)
            ssw = sum(np.sum((v - v.mean()) ** 2) for v in g)
            dfb, dfw = len(g) - 1, len(allx) - len(g)
            msb, msw = ssb / dfb, ssw / dfw
            L += ["H0 : all group means are equal", "H1 : at least one mean differs", "",
                  f"{'Source':<10}{'SS':>14}{'df':>6}{'MS':>14}{'F':>10}{'p':>12}",
                  f"{'Between':<10}{fmt(ssb):>14}{dfb:>6}{fmt(msb):>14}{fmt(r.statistic):>10}{fmt_p(r.pvalue):>12}",
                  f"{'Within':<10}{fmt(ssw):>14}{dfw:>6}{fmt(msw):>14}",
                  f"{'Total':<10}{fmt(ssb + ssw):>14}{dfb + dfw:>6}",
                  f"eta² = SSB/SST = {fmt(ssb / (ssb + ssw))}", "",
                  _decision(float(r.pvalue), alpha),
                  "Assumes normality within groups and equal variances (check Levene below).",
                  ]
            lv = stats.levene(*g)
            L.append(f"Levene test (equal variances): W = {fmt(lv.statistic)}, p {_peq(lv.pvalue)}")
        else:
            r = stats.kruskal(*g)
            L += ["H0 : all groups come from the same distribution", "",
                  f"H = {fmt(r.statistic)},  groups = {len(g)}", "", _decision(float(r.pvalue), alpha)]
    else:
        raise ValueError(f"Unknown test: {name}")
    return "\n".join(L)


# ----- correlation / regression ----------------------------------------------
def pair_clean(df: pd.DataFrame, cx: str, cy: str):
    sub = df[[cx, cy]].dropna()
    return sub[cx].to_numpy(float), sub[cy].to_numpy(float), (sub.index.to_numpy() + 1)


def regression(x: np.ndarray, y: np.ndarray, alpha: float = 0.05, x0: Optional[float] = None):
    n = len(x)
    if n < 3:
        raise ValueError("Regression needs at least 3 complete pairs.")
    xm, ym = x.mean(), y.mean()
    sxx = float(np.sum((x - xm) ** 2))
    syy = float(np.sum((y - ym) ** 2))
    sxy = float(np.sum((x - xm) * (y - ym)))
    if sxx == 0:
        raise ValueError("X is constant - slope undefined.")
    b1 = sxy / sxx
    b0 = ym - b1 * xm
    yhat = b0 + b1 * x
    res = y - yhat
    sse = float(np.sum(res ** 2))
    sst = syy
    ssr = sst - sse
    df = n - 2
    s2 = sse / df
    s = math.sqrt(s2)
    se1 = s / math.sqrt(sxx)
    se0 = s * math.sqrt(1 / n + xm ** 2 / sxx)
    t1 = b1 / se1 if se1 > 0 else float("inf")
    t0 = b0 / se0 if se0 > 0 else float("inf")
    p1 = 2 * stats.t.sf(abs(t1), df)
    p0 = 2 * stats.t.sf(abs(t0), df)
    tc = stats.t.ppf(1 - alpha / 2, df)
    r2 = ssr / sst if sst > 0 else float("nan")
    r = math.copysign(math.sqrt(max(r2, 0)), b1) if sst > 0 else float("nan")
    adj = 1 - (1 - r2) * (n - 1) / df if sst > 0 else float("nan")
    F = ssr / s2 if s2 > 0 else float("inf")
    pF = stats.f.sf(F, 1, df)
    conf = (1 - alpha) * 100
    L = ["SIMPLE LINEAR REGRESSION   y = b0 + b1·x", "=" * 40, "",
         f"n = {n}",
         f"b1 (slope)     = {fmt(b1)}   SE = {fmt(se1)}   t = {fmt(t1)}   p {_peq(p1)}",
         f"                 {conf:g}% CI: ({fmt(b1 - tc * se1)} , {fmt(b1 + tc * se1)})",
         f"b0 (intercept) = {fmt(b0)}   SE = {fmt(se0)}   t = {fmt(t0)}   p {_peq(p0)}",
         f"                 {conf:g}% CI: ({fmt(b0 - tc * se0)} , {fmt(b0 + tc * se0)})", "",
         f"Pearson r = {fmt(r)},   R² = {fmt(r2)},   adjusted R² = {fmt(adj)}",
         f"Residual std error s_e = √(SSE/(n−2)) = {fmt(s)},   df = {df}", "",
         f"{'Source':<12}{'SS':>14}{'df':>6}{'MS':>14}{'F':>12}{'p':>12}",
         f"{'Regression':<12}{fmt(ssr):>14}{1:>6}{fmt(ssr):>14}{fmt(F):>12}{fmt_p(pF):>12}",
         f"{'Residual':<12}{fmt(sse):>14}{df:>6}{fmt(s2):>14}",
         f"{'Total':<12}{fmt(sst):>14}{n - 1:>6}", "",
         f"Sxx = {fmt(sxx)},  Syy = {fmt(syy)},  Sxy = {fmt(sxy)}",
         f"x̄ = {fmt(xm)},  ȳ = {fmt(ym)}"]
    if n >= 3 and np.ptp(res) > 0:
        sw = _quiet(stats.shapiro, res, default=None)
        if sw is not None:
            L.append(f"Shapiro-Wilk on residuals: W = {fmt(sw.statistic)}, p {_peq(sw.pvalue)}")
    if x0 is not None:
        yh = b0 + b1 * x0
        hm = s * math.sqrt(1 / n + (x0 - xm) ** 2 / sxx)
        hp = s * math.sqrt(1 + 1 / n + (x0 - xm) ** 2 / sxx)
        L += ["", f"PREDICTION at x0 = {fmt(x0)}:   ŷ = {fmt(yh)}",
              f"  {conf:g}% CI for mean response : ({fmt(yh - tc * hm)} , {fmt(yh + tc * hm)})",
              f"  {conf:g}% prediction interval  : ({fmt(yh - tc * hp)} , {fmt(yh + tc * hp)})"]
        if x0 < x.min() or x0 > x.max():
            L.append("  WARNING: x0 is outside the observed range (extrapolation).")
    return "\n".join(L), dict(b0=b0, b1=b1, s=s, r2=r2, yhat=yhat, res=res, sxx=sxx, xm=xm, tc=tc, n=n)


def corr_report(df: pd.DataFrame, method: str, alpha: float):
    cols = list(df.columns)
    k = len(cols)
    R = np.full((k, k), np.nan)
    P = np.full((k, k), np.nan)
    N = np.zeros((k, k), int)
    fn = {"pearson": stats.pearsonr, "spearman": stats.spearmanr, "kendall": stats.kendalltau}[method]
    for i in range(k):
        for j in range(i, k):
            sub = df[[cols[i], cols[j]]].dropna()
            N[i, j] = N[j, i] = len(sub)
            if i == j:
                R[i, j], P[i, j] = 1.0, 0.0
                continue
            if len(sub) >= 3 and sub.iloc[:, 0].nunique() > 1 and sub.iloc[:, 1].nunique() > 1:
                r = _quiet(fn, sub.iloc[:, 0], sub.iloc[:, 1], default=None)
                if r is not None:
                    R[i, j] = R[j, i] = float(r[0])
                    P[i, j] = P[j, i] = float(r[1])
    COV = df.cov().to_numpy()
    return cols, R, P, N, COV


def fmt_matrix(labels: List[str], M: np.ndarray, width: int = 12, digits: int = 4) -> str:
    lab = [str(l)[:width] for l in labels]
    w = max(width, 8) + 1
    head = " " * (w) + "".join(f"{l:>{w}}" for l in lab)
    out = [head]
    for i, l in enumerate(lab):
        cells = []
        for j in range(len(lab)):
            v = M[i, j]
            cells.append(f"{'-':>{w}}" if not np.isfinite(v) else f"{fmt(v, digits):>{w}}")
        out.append(f"{l:<{w}}" + "".join(cells))
    return "\n".join(out)


# ----------------------------------------------------------------------------
# Probability calculator registry
# ----------------------------------------------------------------------------
@dataclass
class DistSpec:
    name: str
    discrete: bool
    params: List[Tuple[str, float]]
    factory: Callable
    note: str = ""
    estimator: Optional[Callable] = None


def _req(cond: bool, msg: str):
    if not cond:
        raise ValueError(msg)


def _mk_normal(m, s):
    _req(s > 0, "σ must be > 0")
    return stats.norm(m, s)


def _mk_t(df):
    _req(df > 0, "ν must be > 0")
    return stats.t(df)


def _mk_chi2(df):
    _req(df > 0, "ν must be > 0")
    return stats.chi2(df)


def _mk_f(d1, d2):
    _req(d1 > 0 and d2 > 0, "df must be > 0")
    return stats.f(d1, d2)


def _mk_expon(lam):
    _req(lam > 0, "λ must be > 0")
    return stats.expon(scale=1 / lam)


def _mk_uniform(a, b):
    _req(b > a, "need b > a")
    return stats.uniform(a, b - a)


def _mk_gamma(k, lam):
    _req(k > 0 and lam > 0, "shape and rate must be > 0")
    return stats.gamma(k, scale=1 / lam)


def _mk_weibull(k, eta):
    _req(k > 0 and eta > 0, "shape and scale must be > 0")
    return stats.weibull_min(k, scale=eta)


def _mk_lognorm(mu, sg):
    _req(sg > 0, "σ must be > 0")
    return stats.lognorm(s=sg, scale=math.exp(mu))


def _mk_beta(a, b):
    _req(a > 0 and b > 0, "α, β must be > 0")
    return stats.beta(a, b)


def _mk_binom(n, p):
    _req(n >= 0 and float(n).is_integer(), "n must be a non-negative integer")
    _req(0 <= p <= 1, "p must be in [0, 1]")
    return stats.binom(int(n), p)


def _mk_poisson(lam):
    _req(lam > 0, "λ must be > 0")
    return stats.poisson(lam)


def _mk_geom(p):
    _req(0 < p <= 1, "p must be in (0, 1]")
    return stats.geom(p)


def _mk_nbinom(r, p):
    _req(r >= 1 and float(r).is_integer(), "r must be an integer ≥ 1")
    _req(0 < p <= 1, "p must be in (0, 1]")
    return stats.nbinom(int(r), p, loc=int(r))


def _mk_hyper(N, K, n):
    _req(all(float(v).is_integer() for v in (N, K, n)), "N, K, n must be integers")
    _req(0 <= K <= N and 0 <= n <= N, "need 0 ≤ K ≤ N and 0 ≤ n ≤ N")
    return stats.hypergeom(int(N), int(K), int(n))


def _fit_pos(dist, x, *a):
    return dist.fit(x, floc=0)


DISTRIBUTIONS: List[DistSpec] = [
    DistSpec("Normal", False, [("mean μ", 0.0), ("std dev σ", 1.0)], _mk_normal,
             "X ~ N(μ, σ²)", lambda x: (x.mean(), x.std(ddof=1))),
    DistSpec("Student t", False, [("df ν", 10.0)], _mk_t, "t-distribution"),
    DistSpec("Chi-square", False, [("df ν", 5.0)], _mk_chi2, "χ²(ν)"),
    DistSpec("F", False, [("df1", 5.0), ("df2", 10.0)], _mk_f, "F(d1, d2)"),
    DistSpec("Exponential", False, [("rate λ", 1.0)], _mk_expon, "mean = 1/λ",
             lambda x: (1 / x.mean(),)),
    DistSpec("Uniform (continuous)", False, [("a (min)", 0.0), ("b (max)", 1.0)], _mk_uniform,
             "X ~ U(a, b)", lambda x: (x.min(), x.max())),
    DistSpec("Gamma", False, [("shape k", 2.0), ("rate λ", 1.0)], _mk_gamma, "mean = k/λ",
             lambda x: (lambda p: (p[0], 1 / p[2]))(stats.gamma.fit(x, floc=0))),
    DistSpec("Weibull", False, [("shape β", 1.5), ("scale η", 1.0)], _mk_weibull, "2-parameter Weibull",
             lambda x: (lambda p: (p[0], p[2]))(stats.weibull_min.fit(x, floc=0))),
    DistSpec("Lognormal", False, [("μ of ln X", 0.0), ("σ of ln X", 1.0)], _mk_lognorm,
             "ln X ~ N(μ, σ²)", lambda x: (np.log(x).mean(), np.log(x).std(ddof=1))),
    DistSpec("Beta", False, [("α", 2.0), ("β", 5.0)], _mk_beta, "support [0, 1]"),
    DistSpec("Binomial", True, [("trials n", 10.0), ("p", 0.5)], _mk_binom, "successes in n trials"),
    DistSpec("Poisson", True, [("rate λ", 3.0)], _mk_poisson, "events per interval",
             lambda x: (x.mean(),)),
    DistSpec("Geometric", True, [("p", 0.3)], _mk_geom, "trials until 1st success (1, 2, …)",
             lambda x: (1 / x.mean(),)),
    DistSpec("Negative binomial", True, [("successes r", 3.0), ("p", 0.5)], _mk_nbinom,
             "trials until r-th success (r, r+1, …)"),
    DistSpec("Hypergeometric", True, [("population N", 50.0), ("successes K", 10.0), ("draws n", 5.0)],
             _mk_hyper, "successes in n draws without replacement"),
]
DIST_BY_NAME = {d.name: d for d in DISTRIBUTIONS}


def prob_calc(spec: DistSpec, params: List[float], x: Optional[float], a: Optional[float],
              b: Optional[float], p: Optional[float]):
    """Return (report_text, dist_object)."""
    d = spec.factory(*params)
    pname = ", ".join(f"{lab.split()[0]} = {fmt(v)}" for (lab, _), v in zip(spec.params, params))
    L = [f"{spec.name}({pname})", "=" * 40]
    mv = d.stats(moments="mvsk")
    mean, var, skew, kurt = (float(v) for v in mv)
    L += [f"Mean      E[X]   = {fmt(mean)}", f"Variance  Var[X] = {fmt(var)}",
          f"Std dev          = {fmt(math.sqrt(var) if var >= 0 else float('nan'))}",
          f"Skewness         = {fmt(skew)}", f"Excess kurtosis  = {fmt(kurt)}",
          f"Median           = {fmt(float(d.median()))}"]
    if spec.discrete:
        lo, hi = int(d.ppf(1e-9)), int(d.ppf(1 - 1e-9))
        hi = min(hi, lo + 200000)
        ks = np.arange(lo, hi + 1)
        L.append(f"Mode             = {fmt(float(ks[np.argmax(d.pmf(ks))]))}")
    if x is not None:
        L += ["", f"At x = {fmt(x)}:"]
        if spec.discrete:
            L.append(f"  P(X = x)  = {fmt(float(d.pmf(x)))}")
            L += [f"  P(X ≤ x)  = {fmt(float(d.cdf(x)))}",
                  f"  P(X < x)  = {fmt(float(d.cdf(math.ceil(x) - 1)))}",
                  f"  P(X ≥ x)  = {fmt(float(d.sf(math.ceil(x) - 1)))}",
                  f"  P(X > x)  = {fmt(float(d.sf(x)))}"]
        else:
            L += [f"  f(x)      = {fmt(float(d.pdf(x)))}   (density, not a probability)",
                  f"  P(X ≤ x)  = P(X < x) = {fmt(float(d.cdf(x)))}",
                  f"  P(X ≥ x)  = P(X > x) = {fmt(float(d.sf(x)))}"]
    if a is not None and b is not None:
        if b < a:
            a, b = b, a
        if spec.discrete:
            pr = float(d.cdf(math.floor(b)) - d.cdf(math.ceil(a) - 1))
            L += ["", f"P({fmt(a)} ≤ X ≤ {fmt(b)}) = {fmt(pr)}",
                  f"P({fmt(a)} < X < {fmt(b)}) = {fmt(float(d.cdf(math.ceil(b) - 1) - d.cdf(math.floor(a))))}"]
        else:
            L += ["", f"P({fmt(a)} ≤ X ≤ {fmt(b)}) = {fmt(float(d.cdf(b) - d.cdf(a)))}",
                  f"P(X < {fmt(a)} or X > {fmt(b)}) = {fmt(float(d.cdf(a) + d.sf(b)))}"]
    if p is not None:
        _req(0 < p < 1, "probability p must be in (0, 1)")
        if spec.discrete:
            L += ["", f"Quantile for p = {fmt(p)}:",
                  f"  smallest x with P(X ≤ x) ≥ p   ->   x = {fmt(float(d.ppf(p)))}",
                  f"  smallest x with P(X > x) ≤ p   ->   x = {fmt(float(d.isf(p)))}"]
        else:
            L += ["", f"Quantile for p = {fmt(p)}:",
                  f"  x such that P(X ≤ x) = p   ->   x = {fmt(float(d.ppf(p)))}",
                  f"  upper-tail  P(X > x) = p   ->   x = {fmt(float(d.isf(p)))}"]
        if not spec.discrete:
            L.append(f"  central {fmt(1 - p)} interval            ->   "
                     f"({fmt(float(d.ppf(p / 2)))} , {fmt(float(d.ppf(1 - p / 2)))})")
    return "\n".join(L), d


def empirical_report(x, xv, a, b, p) -> str:
    x = clean(x)
    n = len(x)
    if n == 0:
        return ""
    L = [f"EMPIRICAL (sample X, n = {n})", "=" * 40]
    if xv is not None:
        L += [f"P̂(X ≤ {fmt(xv)}) = {fmt(float(np.mean(x <= xv)))}   ({int(np.sum(x <= xv))}/{n})",
              f"P̂(X < {fmt(xv)}) = {fmt(float(np.mean(x < xv)))}",
              f"P̂(X ≥ {fmt(xv)}) = {fmt(float(np.mean(x >= xv)))}",
              f"P̂(X > {fmt(xv)}) = {fmt(float(np.mean(x > xv)))}",
              f"P̂(X = {fmt(xv)}) = {fmt(float(np.mean(x == xv)))}"]
    if a is not None and b is not None:
        lo, hi = min(a, b), max(a, b)
        L.append(f"P̂({fmt(lo)} ≤ X ≤ {fmt(hi)}) = {fmt(float(np.mean((x >= lo) & (x <= hi))))}")
    if p is not None and 0 < p < 1:
        L.append(f"Sample quantile (p = {fmt(p)}) = {fmt(float(np.quantile(x, p)))}")
    return "\n".join(L)


# ============================================================================
# EXTENDED ENGINE  (SPC, reliability, regression+, resampling, transforms)
# ============================================================================
from scipy import optimize, special


def parse_list(s) -> List[float]:
    toks = [t for t in re.split(r"[,\s;]+", str(s).strip()) if t]
    try:
        return [float(t) for t in toks]
    except ValueError:
        raise ValueError(f"Cannot parse a list of numbers from: '{s}'")


def tolerance_k(n: int, coverage: float, conf: float) -> float:
    """Two-sided normal tolerance factor (Howe's approximation)."""
    nu = n - 1
    z = stats.norm.ppf((1 + coverage) / 2)
    return float(z * math.sqrt(nu * (1 + 1 / n) / stats.chi2.ppf(1 - conf, nu)))


# ----- control-chart constants (exact numerical integration, 5 decimals) -------
_D2 = {2: 1.12838, 3: 1.69257, 4: 2.05875, 5: 2.32593, 6: 2.53441, 7: 2.70436, 8: 2.8472, 9: 2.97003,
       10: 3.07751, 11: 3.17287, 12: 3.25846, 13: 3.33598, 14: 3.40676, 15: 3.47183, 16: 3.53198, 17: 3.58788,
       18: 3.64006, 19: 3.68896, 20: 3.73495, 21: 3.77834, 22: 3.81938, 23: 3.85832, 24: 3.89535, 25: 3.93063}
_D3 = {2: 0.8525, 3: 0.88837, 4: 0.87981, 5: 0.86408, 6: 0.84804, 7: 0.83321, 8: 0.81983, 9: 0.80783,
       10: 0.79705, 11: 0.78731, 12: 0.77848, 13: 0.77042, 14: 0.76302, 15: 0.75621, 16: 0.74991, 17: 0.74405,
       18: 0.73859, 19: 0.73348, 20: 0.72869, 21: 0.72417, 22: 0.71991, 23: 0.71589, 24: 0.71207, 25: 0.70844}


def d2(n: int) -> float:
    """E[range of n standard normals] (n = 2..25)."""
    return _D2[int(n)]


def d3(n: int) -> float:
    """SD of the range of n standard normals (n = 2..25)."""
    return _D3[int(n)]


def c4(n: int) -> float:
    return math.sqrt(2 / (n - 1)) * math.exp(special.gammaln(n / 2) - special.gammaln((n - 1) / 2))


def nelson_rules(v, cl: float, sig: float) -> dict:
    v = np.asarray(v, float)
    n = len(v)
    out = {}
    if sig <= 0 or n < 2:
        return out
    z = (v - cl) / sig
    out["Rule 1  point beyond 3σ"] = list(np.flatnonzero(np.abs(z) > 3) + 1)
    fl, run, prev = [], 0, 0
    for i, s in enumerate(np.sign(z)):
        run = run + 1 if (s != 0 and s == prev) else (1 if s != 0 else 0)
        prev = s
        if run >= 9:
            fl.append(i + 1)
    out["Rule 2  9 in a row on one side of the centre line"] = fl
    fl, d = [], np.diff(v)
    for sign in (1, -1):
        run = 0
        for i, dv in enumerate(d):
            run = run + 1 if dv * sign > 0 else 0
            if run >= 5:
                fl.append(i + 2)
    out["Rule 3  6 in a row steadily increasing/decreasing"] = sorted(set(fl))
    for name, w, thr, need in (("Rule 5  2 of 3 beyond 2σ (same side)", 3, 2, 2),
                               ("Rule 6  4 of 5 beyond 1σ (same side)", 5, 1, 4)):
        fl = set()
        for i in range(max(n - w + 1, 0)):
            for sign in (1, -1):
                beyond = [j for j in range(i, i + w) if sign * z[j] > thr]
                if len(beyond) >= need:
                    fl.update(j + 1 for j in beyond)
        out[name] = sorted(fl)
    return out


def control_chart(kind: str, x=None, n: int = 5, matrix=None) -> dict:
    """kind: 'I-MR' | 'Xbar-R' | 'Xbar-S'."""
    if kind == "I-MR":
        x = clean(x)
        if len(x) < 3:
            raise ValueError("I-MR chart needs at least 3 observations.")
        mr = np.abs(np.diff(x))
        mrbar = float(mr.mean())
        sigma = mrbar / d2(2)
        cl = float(x.mean())
        D4 = 1 + 3 * d3(2) / d2(2)
        return dict(kind=kind, k=len(x), n=1, vals1=x, cl1=cl, ucl1=cl + 3 * sigma, lcl1=cl - 3 * sigma,
                    title1="Individuals (I) chart", vals2=mr, cl2=mrbar, ucl2=D4 * mrbar, lcl2=0.0,
                    title2="Moving range (MR, span 2)", sigma=sigma, xbarbar=cl, sub_x=None)
    if matrix is None:
        x = clean(x)
        if n < 2 or n > 25:
            raise ValueError("Subgroup size must be between 2 and 25.")
        k = len(x) // n
        if k < 2:
            raise ValueError(f"Need at least 2 complete subgroups of size {n} (have {len(x)} values).")
        matrix = x[:k * n].reshape(k, n)
    matrix = np.asarray(matrix, float)
    k, n = matrix.shape
    if n < 2 or n > 25 or k < 2:
        raise ValueError("Need ≥ 2 subgroups with 2–25 observations each.")
    xb = matrix.mean(axis=1)
    xbb = float(xb.mean())
    if kind == "Xbar-R":
        r = np.ptp(matrix, axis=1)
        rbar = float(r.mean())
        sigma = rbar / d2(n)
        a = 3 * sigma / math.sqrt(n)
        D3 = max(0.0, 1 - 3 * d3(n) / d2(n))
        D4 = 1 + 3 * d3(n) / d2(n)
        return dict(kind=kind, k=k, n=n, vals1=xb, cl1=xbb, ucl1=xbb + a, lcl1=xbb - a,
                    title1=f"X̄ chart (subgroup size {n})", vals2=r, cl2=rbar, ucl2=D4 * rbar,
                    lcl2=D3 * rbar, title2="Range (R) chart", sigma=sigma, xbarbar=xbb, sub_x=matrix)
    s = matrix.std(axis=1, ddof=1)
    sbar = float(s.mean())
    c = c4(n)
    sigma = sbar / c
    a = 3 * sigma / math.sqrt(n)
    B3 = max(0.0, 1 - 3 * math.sqrt(1 - c * c) / c)
    B4 = 1 + 3 * math.sqrt(1 - c * c) / c
    return dict(kind=kind, k=k, n=n, vals1=xb, cl1=xbb, ucl1=xbb + a, lcl1=xbb - a,
                title1=f"X̄ chart (subgroup size {n})", vals2=s, cl2=sbar, ucl2=B4 * sbar,
                lcl2=B3 * sbar, title2="Standard deviation (S) chart", sigma=sigma, xbarbar=xbb, sub_x=matrix)


def spc_report(ch: dict) -> str:
    L = [f"CONTROL CHART:  {ch['kind']}   (subgroups k = {ch['k']}, size n = {ch['n']})", "=" * 56,
         f"{ch['title1']}:  CL = {fmt(ch['cl1'])},  UCL = {fmt(ch['ucl1'])},  LCL = {fmt(ch['lcl1'])}",
         f"{ch['title2']}:  CL = {fmt(ch['cl2'])},  UCL = {fmt(ch['ucl2'])},  LCL = {fmt(ch['lcl2'])}",
         f"Within-subgroup sigma estimate = {fmt(ch['sigma'])}", "",
         "NELSON RULES on the first chart (σ = (UCL − CL)/3):"]
    sig1 = (ch["ucl1"] - ch["cl1"]) / 3
    bad_any = False
    for name, idx in nelson_rules(ch["vals1"], ch["cl1"], sig1).items():
        if idx:
            bad_any = True
            L.append(f"  WARNING  {name}: points {', '.join(map(str, idx[:25]))}" + (" ..." if len(idx) > 25 else ""))
        else:
            L.append(f"  ok       {name}")
    v2 = ch["vals2"]
    out2 = list(np.flatnonzero((v2 > ch["ucl2"]) | (v2 < ch["lcl2"])) + 1)
    L.append(f"  {'WARNING' if out2 else 'ok     '}  second chart beyond limits: "
             + (", ".join(map(str, out2)) if out2 else "none"))
    if bad_any or out2:
        L += ["", "WARNING: the process shows signs of special-cause variation - investigate before "
                  "trusting capability indices."]
    else:
        L += ["", "No rule violations: the process appears to be in statistical control."]
    return "\n".join(L)


def capability(x, lsl: Optional[float], usl: Optional[float], target: Optional[float],
               sigma_within: float, alpha: float = 0.05) -> str:
    x = clean(x)
    n = len(x)
    if lsl is None and usl is None:
        raise ValueError("Enter at least one specification limit (LSL and/or USL).")
    if lsl is not None and usl is not None and usl <= lsl:
        raise ValueError("USL must be greater than LSL.")
    mu, so = float(x.mean()), float(x.std(ddof=1))
    sw = sigma_within
    z = stats.norm.ppf(1 - alpha / 2)
    L = ["PROCESS CAPABILITY  (assumes a normal, stable process)", "=" * 56,
         f"n = {n},  mean = {fmt(mu)},  s_overall = {fmt(so)},  σ_within = {fmt(sw)}",
         f"LSL = {fmt(lsl) if lsl is not None else '-'},  USL = {fmt(usl) if usl is not None else '-'}"
         + (f",  target = {fmt(target)}" if target is not None else ""), ""]

    def idx(s):
        up = (usl - mu) / (3 * s) if usl is not None else None
        lo = (mu - lsl) / (3 * s) if lsl is not None else None
        cp = (usl - lsl) / (6 * s) if (usl is not None and lsl is not None) else None
        k = min(v for v in (up, lo) if v is not None)
        return cp, up, lo, k

    for tag, s, name in (("Cp", sw, "POTENTIAL (within)"), ("Pp", so, "OVERALL (long-term)")):
        cp, up, lo, k = idx(s)
        L.append(f"{name}")
        if cp is not None:
            lo_ci = cp * math.sqrt(stats.chi2.ppf(alpha / 2, n - 1) / (n - 1))
            hi_ci = cp * math.sqrt(stats.chi2.ppf(1 - alpha / 2, n - 1) / (n - 1))
            L.append(f"  {tag}  = {fmt(cp)}    {(1 - alpha) * 100:g}% CI ({fmt(lo_ci)} , {fmt(hi_ci)})")
        if up is not None:
            L.append(f"  {tag}u = {fmt(up)}")
        if lo is not None:
            L.append(f"  {tag}l = {fmt(lo)}")
        half = z * math.sqrt(1 / (9 * n) + k * k / (2 * (n - 1)))
        L.append(f"  {tag}k = {fmt(k)}    approx. {(1 - alpha) * 100:g}% CI ({fmt(k - half)} , {fmt(k + half)})")
    if target is not None and lsl is not None and usl is not None:
        cpm = (usl - lsl) / (6 * math.sqrt(so ** 2 + (mu - target) ** 2))
        L.append(f"Taguchi Cpm (centring on target) = {fmt(cpm)}")
    below = stats.norm.cdf(lsl, mu, so) if lsl is not None else 0.0
    above = stats.norm.sf(usl, mu, so) if usl is not None else 0.0
    tot = below + above
    ob_b = float(np.mean(x < lsl)) if lsl is not None else 0.0
    ob_a = float(np.mean(x > usl)) if usl is not None else 0.0
    bw = stats.norm.cdf(lsl, mu, sw) if lsl is not None else 0.0
    aw = stats.norm.sf(usl, mu, sw) if usl is not None else 0.0
    L += ["", "NON-CONFORMANCE (parts per million)",
          f"  observed          below LSL {fmt(ob_b * 1e6)},  above USL {fmt(ob_a * 1e6)},  total {fmt((ob_a + ob_b) * 1e6)}",
          f"  expected overall  below LSL {fmt(below * 1e6)},  above USL {fmt(above * 1e6)},  total {fmt(tot * 1e6)}",
          f"  expected within   total {fmt((bw + aw) * 1e6)}",
          f"  process yield (overall) = {fmt((1 - tot) * 100)} %" +
          (f",   Z.bench = {fmt(float(stats.norm.isf(max(tot, 1e-300))))}" if tot > 0 else "")]
    sh = _quiet(stats.shapiro, x, default=None)
    if sh is not None:
        L.append(f"Normality check (Shapiro-Wilk): p {_peq(sh.pvalue)}" +
                 ("   WARNING: data look non-normal - indices may mislead." if sh.pvalue < alpha else ""))
    k = idx(so)[3]
    L.append("Rule of thumb: Cpk ≥ 1.33 capable, 1.00–1.33 marginal, < 1.00 not capable "
             f"(here Ppk = {fmt(k)}).")
    return "\n".join(L)


# ----- reliability -----------------------------------------------------------
def weibull_mle(t, event=None):
    t = np.asarray(t, float)
    ev = np.ones_like(t) if event is None else np.asarray(event, float)
    if np.any(t <= 0):
        raise ValueError("Weibull analysis needs positive times (all > 0).")
    r = int(ev.sum())
    if r < 2:
        raise ValueError("Need at least 2 observed failures.")
    lt = np.log(t)

    def nll(th):
        lb, le = th
        b = math.exp(lb)
        zz = np.exp(b * (lt - le))
        return -(np.sum(ev * (lb - b * le + (b - 1) * lt)) - np.sum(zz))

    try:
        c, _, sc = stats.weibull_min.fit(t[ev > 0], floc=0)
    except Exception:
        c, sc = 1.5, float(t.mean())
    res = optimize.minimize(nll, [math.log(max(c, 0.2)), math.log(max(sc, 1e-9))], method="Nelder-Mead",
                            options=dict(xatol=1e-10, fatol=1e-12, maxiter=5000))
    th = res.x
    h = 1e-4
    H = np.zeros((2, 2))
    f0 = nll(th)
    for i in range(2):
        for j in range(2):
            ei, ej = np.eye(2)[i] * h, np.eye(2)[j] * h
            H[i, j] = (nll(th + ei + ej) - nll(th + ei - ej) - nll(th - ei + ej) + nll(th - ei - ej)) / (4 * h * h)
    try:
        cov = np.linalg.inv(H)
    except np.linalg.LinAlgError:
        cov = np.full((2, 2), np.nan)
    return dict(lnb=float(th[0]), lne=float(th[1]), beta=math.exp(th[0]), eta=math.exp(th[1]), cov=cov,
                ll=-f0, n=len(t), r=r, c=len(t) - r)


def johnson_ranks(t, event):
    t = np.asarray(t, float)
    ev = np.asarray(event, float)
    order = np.argsort(t, kind="stable")
    t, ev = t[order], ev[order]
    n = len(t)
    prev = 0.0
    ts, ranks = [], []
    for i in range(n):
        if ev[i] > 0:
            rev = n - i
            prev = (rev * prev + (n + 1)) / (rev + 1)
            ts.append(t[i])
            ranks.append(prev)
    ranks = np.array(ranks)
    return np.array(ts), (ranks - 0.3) / (n + 0.4)


def weibull_report(t, event, t0: Optional[float], alpha: float):
    ev = np.ones(len(t)) if event is None else np.asarray(event, float)
    res = weibull_mle(t, ev)
    b, eta, cov = res["beta"], res["eta"], res["cov"]
    z = stats.norm.ppf(1 - alpha / 2)
    se = np.sqrt(np.diag(cov))
    cl = f"{(1 - alpha) * 100:g}% CI"
    L = ["WEIBULL ANALYSIS  (maximum likelihood, right-censoring supported)", "=" * 58,
         f"units = {res['n']},  failures = {res['r']},  censored (suspended) = {res['c']}",
         f"log-likelihood = {fmt(res['ll'])}", "",
         f"shape β = {fmt(b)}    {cl} ({fmt(b * math.exp(-z * se[0]))} , {fmt(b * math.exp(z * se[0]))})",
         f"scale η = {fmt(eta)}    {cl} ({fmt(eta * math.exp(-z * se[1]))} , {fmt(eta * math.exp(z * se[1]))})",
         ("β < 1: infant mortality (decreasing hazard)" if b < 1 else
          "β ≈ 1: random failures (constant hazard)" if abs(b - 1) < 0.05 else
          "β > 1: wear-out (increasing hazard)"), ""]
    mttf = eta * math.gamma(1 + 1 / b)
    g = np.array([-math.exp(-res["lnb"]) * float(special.digamma(1 + 1 / b)), 1.0])
    sm = math.sqrt(float(g @ cov @ g))
    L.append(f"MTTF = η·Γ(1+1/β) = {fmt(mttf)}    {cl} ({fmt(mttf * math.exp(-z * sm))} , {fmt(mttf * math.exp(z * sm))})")
    L.append(f"median life (B50) = {fmt(eta * math.log(2) ** (1 / b))}")
    for p in (0.01, 0.05, 0.10):
        c_ = math.log(-math.log(1 - p))
        tp = eta * (-math.log(1 - p)) ** (1 / b)
        g = np.array([-math.exp(-res["lnb"]) * c_, 1.0])
        s_ = math.sqrt(float(g @ cov @ g))
        L.append(f"B{p * 100:g} life (reliability {1 - p:g}) = {fmt(tp)}    {cl} ({fmt(tp * math.exp(-z * s_))} , {fmt(tp * math.exp(z * s_))})")
    if t0 is not None and t0 > 0:
        w = b * (math.log(t0) - math.log(eta))
        g = np.array([w, -b])
        sw = math.sqrt(float(g @ cov @ g))
        R = math.exp(-math.exp(w))
        L += ["", f"AT MISSION TIME t = {fmt(t0)}",
              f"  reliability R(t) = {fmt(R)}    {cl} ({fmt(math.exp(-math.exp(w + z * sw)))} , {fmt(math.exp(-math.exp(w - z * sw)))})",
              f"  unreliability F(t) = {fmt(1 - R)}",
              f"  hazard rate h(t) = {fmt(b / eta * (t0 / eta) ** (b - 1))}  per unit time"]
    T = float(np.sum(t))
    r = res["r"]
    if res["c"] == 0:
        lo_, hi_ = 2 * T / stats.chi2.ppf(1 - alpha / 2, 2 * r), 2 * T / stats.chi2.ppf(alpha / 2, 2 * r)
        kind = "failure-terminated"
    else:
        lo_, hi_ = 2 * T / stats.chi2.ppf(1 - alpha / 2, 2 * r + 2), 2 * T / stats.chi2.ppf(alpha / 2, 2 * r)
        kind = "time-terminated"
    L += ["", f"EXPONENTIAL MODEL (constant hazard, {kind}):",
          f"  MTBF = total time / failures = {fmt(T / r)}    {cl} ({fmt(lo_)} , {fmt(hi_)})",
          f"  failure rate λ = {fmt(r / T)}"]
    return "\n".join(L), res


# ----- multiple / polynomial regression ---------------------------------------
def multi_regression(df: pd.DataFrame, y: str, preds: List[str], alpha: float = 0.05, degree: int = 1,
                     center: bool = False, x0: Optional[List[float]] = None):
    if not preds:
        raise ValueError("Select at least one predictor.")
    if y in preds:
        raise ValueError("The response Y must not be among the predictors.")
    sub = df[[y] + preds].dropna()
    Y = sub[y].to_numpy(float)
    n = len(Y)
    names, cols, means = ["(intercept)"], [np.ones(n)], {}
    for p in preds:
        v = sub[p].to_numpy(float)
        m = v.mean() if center else 0.0
        means[p] = m
        for d in range(1, degree + 1):
            names.append(p if d == 1 else f"{p}^{d}")
            cols.append((v - m) ** d)
    X = np.column_stack(cols)
    k = X.shape[1]
    if n <= k:
        raise ValueError(f"Need more observations (n = {n}) than model terms ({k}).")
    if np.linalg.matrix_rank(X) < k:
        raise ValueError("Perfect multicollinearity (rank-deficient design): some predictors/terms are exact linear "
                         "combinations of others. Remove redundant predictors (note: squaring a 0/1 variable "
                         "duplicates it - use degree 1 for indicator columns).")
    XtXi = np.linalg.inv(X.T @ X)
    b = XtXi @ X.T @ Y
    yh = X @ b
    e = Y - yh
    sse = float(e @ e)
    sst = float(np.sum((Y - Y.mean()) ** 2))
    ssr = sst - sse
    dfe = n - k
    s2 = sse / dfe
    se = np.sqrt(np.diag(XtXi) * s2)
    t = b / se
    p = 2 * stats.t.sf(np.abs(t), dfe)
    tc = stats.t.ppf(1 - alpha / 2, dfe)
    r2 = ssr / sst
    adj = 1 - (1 - r2) * (n - 1) / dfe
    Fv = (ssr / (k - 1)) / s2 if k > 1 else float("nan")
    pF = stats.f.sf(Fv, k - 1, dfe) if k > 1 else float("nan")
    h = np.einsum("ij,jk,ik->i", X, XtXi, X)
    h = np.clip(h, 0, 1 - 1e-12)
    press = float(np.sum((e / (1 - h)) ** 2))
    stud = e / np.sqrt(s2 * (1 - h))
    cook = e ** 2 / (k * s2) * h / (1 - h) ** 2
    dw = float(np.sum(np.diff(e) ** 2) / sse) if sse > 0 else float("nan")
    aic = n * math.log(sse / n) + 2 * k
    bic = n * math.log(sse / n) + k * math.log(n)
    nonint = X[:, 1:]
    if nonint.shape[1] >= 2:
        vif = np.diag(np.linalg.inv(np.corrcoef(nonint, rowvar=False)))
    else:
        vif = np.array([1.0]) if nonint.shape[1] == 1 else np.array([])
    sdy = Y.std(ddof=1)
    L = ["MULTIPLE LINEAR REGRESSION", "=" * 78,
         f"Y = {y};  predictors = {', '.join(preds)};  polynomial degree = {degree}"
         + ("  (centred)" if center else "") + f";  n = {n}", "",
         f"{'Term':<18}{'Coef':>12}{'SE':>12}{'t':>10}{'p':>12}{'CI low':>12}{'CI high':>12}{'VIF':>8}{'Std beta':>10}"]
    for i, nm in enumerate(names):
        v = fmt(vif[i - 1], 4) if i >= 1 else ""
        sb = fmt(b[i] * X[:, i].std(ddof=1) / sdy, 4) if i >= 1 else ""
        L.append(f"{nm[:17]:<18}{fmt(b[i]):>12}{fmt(se[i]):>12}{fmt(t[i], 4):>10}{fmt_p(p[i]):>12}"
                 f"{fmt(b[i] - tc * se[i]):>12}{fmt(b[i] + tc * se[i]):>12}{v:>8}{sb:>10}")
    L += ["", f"R² = {fmt(r2)},  adjusted R² = {fmt(adj)},  predicted R² (PRESS) = {fmt(1 - press / sst)}",
          f"residual std error s = {fmt(math.sqrt(s2))} (df = {dfe}),  AIC = {fmt(aic)},  BIC = {fmt(bic)}",
          f"Durbin-Watson = {fmt(dw)}  (≈ 2: no first-order autocorrelation)", "",
          f"{'Source':<12}{'SS':>14}{'df':>6}{'MS':>14}{'F':>12}{'p':>12}",
          f"{'Regression':<12}{fmt(ssr):>14}{k - 1:>6}{fmt(ssr / (k - 1)) if k > 1 else '-':>14}{fmt(Fv):>12}{fmt_p(pF):>12}",
          f"{'Residual':<12}{fmt(sse):>14}{dfe:>6}{fmt(s2):>14}",
          f"{'Total':<12}{fmt(sst):>14}{n - 1:>6}"]
    if len(vif) and float(np.max(vif)) > 10:
        L.append("WARNING: VIF > 10 - strong multicollinearity (try centring or fewer terms).")
    sw = _quiet(stats.shapiro, e, default=None)
    if sw is not None and n >= 3:
        L.append(f"Shapiro-Wilk on residuals: W = {fmt(sw.statistic)}, p {_peq(sw.pvalue)}")
    rows = sub.index.to_numpy() + 1
    fl = [(int(rows[i]), float(stud[i]), float(h[i]), float(cook[i])) for i in range(n)
          if abs(stud[i]) > 3 or h[i] > 2 * k / n or cook[i] > 4 / n]
    L += ["", "INFLUENTIAL / UNUSUAL POINTS  (|studentized residual| > 3, leverage > 2k/n, Cook's D > 4/n)"]
    if fl:
        for r_, s_, h_, c_ in fl[:25]:
            L.append(f"  row {r_}:  student. residual = {fmt(s_, 4)},  leverage = {fmt(h_, 4)},  Cook's D = {fmt(c_, 4)}")
    else:
        L.append("  none flagged")
    if x0 is not None:
        if len(x0) != len(preds):
            raise ValueError(f"Prediction needs {len(preds)} value(s) (one per predictor, in order).")
        row = [1.0]
        for pnm, xv in zip(preds, x0):
            for d in range(1, degree + 1):
                row.append((xv - means[pnm]) ** d)
        row = np.array(row)
        ypred = float(row @ b)
        sm_ = math.sqrt(s2 * float(row @ XtXi @ row))
        sp_ = math.sqrt(s2 * (1 + float(row @ XtXi @ row)))
        cl = f"{(1 - alpha) * 100:g}%"
        L += ["", f"PREDICTION at ({', '.join(fmt(v) for v in x0)}):  ŷ = {fmt(ypred)}",
              f"  {cl} CI for mean response : ({fmt(ypred - tc * sm_)} , {fmt(ypred + tc * sm_)})",
              f"  {cl} prediction interval  : ({fmt(ypred - tc * sp_)} , {fmt(ypred + tc * sp_)})"]
    return "\n".join(L), dict(y=Y, yhat=yh, resid=e, stud=stud, names=names, h=h, cook=cook, n=n, k=k)


# ----- extra hypothesis tests (called from run_test) --------------------------
def extra_test(name: str, a, b, alpha: float, alt: str, mu0: float, groups, names) -> Optional[str]:
    L = [f"TEST: {name}", "=" * (6 + len(name))]
    if name == "Runs test (randomness about the median)":
        x = clean(a)
        med = np.median(x)
        s = x[x != med] > med
        n1, n2 = int(s.sum()), int((~s).sum())
        if n1 < 1 or n2 < 1:
            raise ValueError("Data are constant about the median.")
        runs = 1 + int(np.sum(s[1:] != s[:-1]))
        mu = 2 * n1 * n2 / (n1 + n2) + 1
        var = 2 * n1 * n2 * (2 * n1 * n2 - n1 - n2) / ((n1 + n2) ** 2 * (n1 + n2 - 1))
        z = (runs - mu) / math.sqrt(var) if var > 0 else float("nan")
        p = 2 * stats.norm.sf(abs(z))
        L += ["H0 : the sequence is random (no clustering / alternation)", "",
              f"median = {fmt(med)},  n above = {n1},  n below = {n2}",
              f"runs observed = {runs},  expected = {fmt(mu)},  z = {fmt(z)}", "", _decision(p, alpha),
              "Too few runs suggest trends / clustering; too many suggest alternation." +
              ("  (normal approximation: n1, n2 should be ≥ 10)" if min(n1, n2) < 10 else "")]
    elif name == "Sign test (median)":
        x = clean(a) - mu0
        pos, neg = int((x > 0).sum()), int((x < 0).sum())
        if pos + neg == 0:
            raise ValueError("All values equal the hypothesised median.")
        r = stats.binomtest(pos, pos + neg, 0.5, alternative=alt)
        L += [f"H0 : median = {fmt(mu0)}   (H1: {alt})", f"above = {pos}, below = {neg}, ties dropped = {int((x == 0).sum())}",
              "", _decision(float(r.pvalue), alpha)]
    elif name == "Kolmogorov-Smirnov (two samples)":
        x, y = clean(a), clean(b)
        r = stats.ks_2samp(x, y, alternative=alt)
        L += [f"n_X = {len(x)}, n_Y = {len(y)}", f"D = {fmt(r.statistic)}", "", _decision(float(r.pvalue), alpha)]
    elif name in ("Levene / Brown-Forsythe (all columns)", "Bartlett (all columns)"):
        g = [clean(v) for v in groups if len(clean(v)) > 1]
        if len(g) < 2:
            raise ValueError("Need at least two columns with ≥ 2 values.")
        r = stats.levene(*g, center="median") if name.startswith("Levene") else stats.bartlett(*g)
        L += ["H0 : all group variances are equal", f"groups = {len(g)}, statistic = {fmt(r.statistic)}", "",
              _decision(float(r.pvalue), alpha)]
        if name.startswith("Bartlett"):
            L.append("Bartlett is sensitive to non-normality; Levene is more robust.")
    elif name == "Tukey HSD post-hoc (all columns)":
        keep = [(nm, clean(v)) for nm, v in zip(names, groups) if len(clean(v)) > 1]
        if len(keep) < 3:
            raise ValueError("Tukey HSD needs at least three columns.")
        res = stats.tukey_hsd(*[v for _, v in keep])
        ci = res.confidence_interval(confidence_level=1 - alpha)
        L += [f"all pairwise comparisons, family-wise {(1 - alpha) * 100:g}% confidence", "",
              f"{'Pair':<30}{'diff':>12}{'p-adj':>12}{'CI low':>12}{'CI high':>12}  signif."]
        for i in range(len(keep)):
            for j in range(i + 1, len(keep)):
                pv = res.pvalue[i, j]
                L.append(f"{(keep[i][0][:13] + ' - ' + keep[j][0][:13]):<30}{fmt(res.statistic[i, j]):>12}"
                         f"{fmt_p(pv):>12}{fmt(ci.low[i, j]):>12}{fmt(ci.high[i, j]):>12}  {'*' if pv < alpha else ''}")
    else:
        return None
    return "\n".join(L)


# ----- resampling --------------------------------------------------------------
def _stat_funcs():
    q75 = lambda x, axis=-1: np.percentile(x, 75, axis=axis) - np.percentile(x, 25, axis=axis)
    return {
        "mean": lambda x, axis=-1: np.mean(x, axis=axis),
        "median": lambda x, axis=-1: np.median(x, axis=axis),
        "std deviation": lambda x, axis=-1: np.std(x, axis=axis, ddof=1),
        "variance": lambda x, axis=-1: np.var(x, axis=axis, ddof=1),
        "trimmed mean (10%)": lambda x, axis=-1: stats.trim_mean(x, 0.1, axis=axis),
        "IQR": q75,
        "coefficient of variation": lambda x, axis=-1: np.std(x, axis=axis, ddof=1) / np.mean(x, axis=axis),
        "skewness": lambda x, axis=-1: stats.skew(x, axis=axis),
    }


def _corr_axis(x, y, axis=-1):
    xm = x - x.mean(axis=axis, keepdims=True)
    ym = y - y.mean(axis=axis, keepdims=True)
    return (xm * ym).sum(axis=axis) / np.sqrt((xm ** 2).sum(axis=axis) * (ym ** 2).sum(axis=axis))


PAIRED_STATS = {"correlation (X,Y paired)": (_corr_axis, True),
                "mean of differences X−Y (paired)": (lambda x, y, axis=-1: np.mean(x - y, axis=axis), True),
                "difference of means X−Y (independent)": (lambda x, y, axis=-1: np.mean(x, axis=axis) - np.mean(y, axis=axis), False)}
BOOT_STATS = list(_stat_funcs()) + list(PAIRED_STATS)


def bootstrap_report(x, y, stat: str, nboot: int, conf: float, method: str, seed: Optional[int] = 12345):
    rng = np.random.default_rng(seed)
    if stat in PAIRED_STATS:
        if y is None:
            raise ValueError("This statistic needs a Y variable (top bar).")
        fn, paired = PAIRED_STATS[stat]
        data = (np.asarray(x, float), np.asarray(y, float))
        est = float(fn(*data))
        kw = dict(paired=paired)
    else:
        fn = _stat_funcs()[stat]
        data = (clean(x),)
        est = float(fn(data[0]))
        kw = {}
    used = method
    try:
        res = stats.bootstrap(data, fn, n_resamples=nboot, confidence_level=conf, method=method,
                              vectorized=True, axis=-1, random_state=rng, **kw)
    except Exception:
        used = "percentile"
        res = stats.bootstrap(data, fn, n_resamples=nboot, confidence_level=conf, method="percentile",
                              vectorized=True, axis=-1, random_state=rng, **kw)
    dist = res.bootstrap_distribution
    lines = ["BOOTSTRAP", "=" * 40, f"statistic: {stat}", f"sample size: {', '.join(str(len(d)) for d in data)},  resamples = {nboot}",
             f"observed estimate = {fmt(est)}", f"bootstrap SE = {fmt(float(res.standard_error))},  bias = {fmt(float(dist.mean()) - est)}",
             f"{conf * 100:g}% CI ({used}): ({fmt(float(res.confidence_interval.low))} , {fmt(float(res.confidence_interval.high))})",
             "", "BCa corrects for bias and skewness and is usually preferred; the percentile method is simplest."]
    return "\n".join(lines), dist, est, (float(res.confidence_interval.low), float(res.confidence_interval.high))


def permutation_report(x, y, nres: int, alt: str, seed: Optional[int] = 12345):
    x, y = clean(x), clean(y)
    stat = lambda a, b, axis=-1: np.mean(a, axis=axis) - np.mean(b, axis=axis)
    r = stats.permutation_test((x, y), stat, n_resamples=nres, vectorized=True, alternative=alt,
                               random_state=np.random.default_rng(seed))
    lines = ["PERMUTATION TEST  (difference of means X − Y)", "=" * 44, f"n_X = {len(x)}, n_Y = {len(y)}, resamples = {nres}",
             f"observed difference = {fmt(float(r.statistic))}", f"p-value ({alt}) = {fmt_p(float(r.pvalue))}",
             "No normality assumption: the p-value is the share of label shuffles at least as extreme."]
    return "\n".join(lines), r.null_distribution, float(r.statistic)


def clt_demo(spec: DistSpec, params: List[float], n: int, reps: int, seed: Optional[int] = 12345):
    d = spec.factory(*params)
    reps = int(min(reps, max(200, 6_000_000 // max(n, 1))))
    rng = np.random.default_rng(seed)
    means = d.rvs(size=(reps, n), random_state=rng).mean(axis=1)
    mu, var = float(d.mean()), float(d.var())
    se = math.sqrt(var / n)
    sub = means[:5000]
    sw = _quiet(stats.shapiro, sub, default=None)
    L = ["CENTRAL LIMIT THEOREM DEMONSTRATION", "=" * 40,
         f"population: {spec.name}({', '.join(fmt(p) for p in params)}),  mean μ = {fmt(mu)},  σ = {fmt(math.sqrt(var))}",
         f"sample size n = {n},  simulated samples = {reps}", "",
         f"theory      : mean of X̄ = {fmt(mu)},  SE = σ/√n = {fmt(se)}",
         f"simulation  : mean of X̄ = {fmt(float(means.mean()))},  SD of X̄ = {fmt(float(means.std(ddof=1)))}",
         f"skewness of X̄ = {fmt(float(stats.skew(means)))}  (population skewness {fmt(float(d.stats('s')))})"]
    if sw is not None:
        L.append(f"Shapiro-Wilk on simulated means: p {_peq(sw.pvalue)}")
    return "\n".join(L), means, mu, se


# ----- data transformation -----------------------------------------------------
_SAFE_FUNCS = {n: getattr(np, n) for n in ("sqrt", "log", "log10", "log2", "exp", "sin", "cos", "tan", "arcsin",
                                           "arccos", "arctan", "sinh", "cosh", "tanh", "abs", "floor", "ceil",
                                           "round", "where", "clip", "minimum", "maximum", "sign", "power", "cumsum",
                                           "diff", "mean", "std", "var", "median", "sum", "min", "max", "isnan")}
_SAFE_FUNCS.update(pi=math.pi, e=math.e, nan=float("nan"))


def safe_eval(expr: str, df: pd.DataFrame, xname: Optional[str] = None):
    expr = expr.strip()
    if not expr:
        raise ValueError("Enter an expression, e.g.  sqrt(force_N) * 2 + 1")
    if "__" in expr or re.search(r"\.[A-Za-z_]", expr) or re.search(r"\b(import|lambda|exec|eval|open)\b", expr):
        raise ValueError("Attribute access and keywords like import/lambda/open are not allowed in expressions.")
    ns = dict(_SAFE_FUNCS)
    cols = {c: df[c].to_numpy(float) for c in df.columns}
    for c, v in cols.items():
        if str(c).isidentifier():
            ns[c] = v
    ns["col"] = cols
    if xname is not None and xname in cols:
        ns["x"] = cols[xname]
    ns["row"] = np.arange(1, len(df) + 1, dtype=float)
    with np.errstate(all="ignore"):
        try:
            out = eval(expr, {"__builtins__": {}}, ns)
        except Exception as e:
            raise ValueError(f"Expression error: {e}")
    out = np.asarray(out)
    if out.ndim == 0:
        out = np.full(len(df), out)
    if out.shape != (len(df),):
        raise ValueError("The expression must produce one value per row.")
    return out


def transform_series(vals: np.ndarray, op: str, k: int = 3):
    """Apply a named transform to the finite values; NaN positions are kept."""
    out = np.full(len(vals), np.nan)
    m = np.isfinite(vals)
    v = vals[m]
    info = ""
    if v.size == 0:
        raise ValueError("No valid data.")
    if op == "z-score (standardize)":
        r = (v - v.mean()) / v.std(ddof=1)
    elif op == "min-max (0 to 1)":
        r = (v - v.min()) / (v.max() - v.min())
    elif op == "center (subtract mean)":
        r = v - v.mean()
    elif op == "natural log":
        if np.any(v <= 0):
            raise ValueError("ln requires all values > 0.")
        r = np.log(v)
    elif op == "log10":
        if np.any(v <= 0):
            raise ValueError("log10 requires all values > 0.")
        r = np.log10(v)
    elif op == "square root":
        if np.any(v < 0):
            raise ValueError("sqrt requires all values ≥ 0.")
        r = np.sqrt(v)
    elif op == "square":
        r = v ** 2
    elif op == "reciprocal (1/x)":
        if np.any(v == 0):
            raise ValueError("reciprocal requires non-zero values.")
        r = 1 / v
    elif op == "Box-Cox":
        if np.any(v <= 0):
            raise ValueError("Box-Cox requires all values > 0.")
        r, lam = stats.boxcox(v)
        info = f"Box-Cox λ = {fmt(float(lam))}"
    elif op == "Yeo-Johnson":
        r, lam = stats.yeojohnson(v)
        info = f"Yeo-Johnson λ = {fmt(float(lam))}"
    elif op == "rank":
        r = stats.rankdata(v)
    elif op == "cumulative sum":
        r = np.cumsum(v)
    elif op == "first difference":
        r = np.concatenate([[np.nan], np.diff(v)])
    elif op == "moving average (window k)":
        k = max(1, int(k))
        r = pd.Series(v).rolling(k, min_periods=1).mean().to_numpy()
        info = f"trailing moving average, window = {k}"
    else:
        raise ValueError(f"Unknown transform: {op}")
    out[m] = r
    return out, info


TRANSFORMS = ["z-score (standardize)", "min-max (0 to 1)", "center (subtract mean)", "natural log", "log10",
              "square root", "square", "reciprocal (1/x)", "Box-Cox", "Yeo-Johnson", "rank", "cumulative sum",
              "first difference", "moving average (window k)"]


# ============================================================================
# CALCULATORS  (category -> name -> CalcSpec)
# ============================================================================
@dataclass
class CalcSpec:
    fields: list      # (label, default, kind, choices, fill_key)   kind: f i o s c m
    hint: str
    fn: Callable      # fn(values, alpha) -> str


def F(label, default="", kind="f", ch=None, fill=None):
    return (label, str(default), kind, ch, fill)


def _tail_p(cdf_v, sf_v, alt):
    return _p_from_cdf(cdf_v, sf_v, alt)


def _wilson(x, n, a):
    z = stats.norm.ppf(1 - a / 2)
    p = x / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, c - h), min(1.0, c + h)


def _chk_counts(x, n):
    if n < 1 or x < 0 or x > n:
        raise ValueError("Need 0 ≤ x ≤ n and n ≥ 1.")


def calc_prop_ci(v, a):
    x, n = v[0], v[1]
    _chk_counts(x, n)
    p = x / n
    z = stats.norm.ppf(1 - a / 2)
    w = z * math.sqrt(p * (1 - p) / n)
    nt = n + z * z
    pt = (x + z * z / 2) / nt
    ah = z * math.sqrt(pt * (1 - pt) / nt)
    lo_cp = stats.beta.ppf(a / 2, x, n - x + 1) if x > 0 else 0.0
    hi_cp = stats.beta.ppf(1 - a / 2, x + 1, n - x) if x < n else 1.0
    lo_j = stats.beta.ppf(a / 2, x + .5, n - x + .5) if x > 0 else 0.0
    hi_j = stats.beta.ppf(1 - a / 2, x + .5, n - x + .5) if x < n else 1.0
    wl, wh = _wilson(x, n, a)
    c = f"{(1 - a) * 100:g}%"
    return "\n".join([f"PROPORTION CONFIDENCE INTERVALS   (x = {int(x)}, n = {int(n)}, p̂ = {fmt(p)}, level {c})", "",
                      f"Wald (normal approx.)   ({fmt(max(0, p - w))} , {fmt(min(1, p + w))})   poor for small n or p near 0/1",
                      f"Wilson score            ({fmt(wl)} , {fmt(wh)})   recommended general-purpose",
                      f"Agresti-Coull           ({fmt(max(0, pt - ah))} , {fmt(min(1, pt + ah))})",
                      f"Clopper-Pearson (exact) ({fmt(lo_cp)} , {fmt(hi_cp)})   conservative",
                      f"Jeffreys (Bayesian)     ({fmt(lo_j)} , {fmt(hi_j)})"])


def calc_prop_test(v, a):
    x, n, p0, alt = v[0], v[1], v[2], v[3]
    _chk_counts(x, n)
    if not 0 < p0 < 1:
        raise ValueError("p0 must be in (0, 1).")
    p = x / n
    ex = stats.binomtest(int(x), int(n), p0, alternative=alt)
    z = (p - p0) / math.sqrt(p0 * (1 - p0) / n)
    pz = _tail_p(stats.norm.cdf(z), stats.norm.sf(z), alt)
    ci = ex.proportion_ci(confidence_level=1 - a, method="exact")
    L = ["ONE-PROPORTION TEST", "=" * 24] + _h_lines("", alt, "p", fmt(p0))
    L += ["", f"x = {int(x)}, n = {int(n)}, p̂ = {fmt(p)}", f"z = (p̂ − p0)/√(p0·q0/n) = {fmt(z)}",
          f"exact binomial:  {_decision(float(ex.pvalue), a)}", f"normal approx.:  {_decision(pz, a)}",
          f"exact {(1 - a) * 100:g}% CI for p: ({fmt(ci.low)} , {fmt(ci.high)})"]
    if n * p0 < 10 or n * (1 - p0) < 10:
        L.append("WARNING: n·p0 or n·(1−p0) < 10 - prefer the exact binomial result.")
    return "\n".join(L)


def calc_two_prop(v, a):
    x1, n1, x2, n2, alt = v
    _chk_counts(x1, n1)
    _chk_counts(x2, n2)
    p1, p2 = x1 / n1, x2 / n2
    d = p1 - p2
    pb = (x1 + x2) / (n1 + n2)
    se0 = math.sqrt(pb * (1 - pb) * (1 / n1 + 1 / n2))
    z = d / se0 if se0 > 0 else float("nan")
    p = _tail_p(stats.norm.cdf(z), stats.norm.sf(z), alt)
    zc = stats.norm.ppf(1 - a / 2)
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    l1, u1 = _wilson(x1, n1, a)
    l2, u2 = _wilson(x2, n2, a)
    nl = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    nu = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    fe = stats.fisher_exact([[x1, n1 - x1], [x2, n2 - x2]], alternative=alt)
    L = ["TWO-PROPORTION TEST", "=" * 24] + _h_lines("", alt, "p1 − p2", "0")
    L += ["", f"p̂1 = {fmt(p1)} ({int(x1)}/{int(n1)}),  p̂2 = {fmt(p2)} ({int(x2)}/{int(n2)}),  difference = {fmt(d)}",
          f"pooled z-test:  z = {fmt(z)}   {_decision(p, a)}", f"Fisher exact:   {_decision(float(fe.pvalue), a)}",
          f"{(1 - a) * 100:g}% CI for p1 − p2:  Wald ({fmt(d - zc * se)} , {fmt(d + zc * se)}),  Newcombe ({fmt(nl)} , {fmt(nu)})"]
    if p2 > 0 and p1 > 0:
        rr = p1 / p2
        s_ = math.sqrt((1 - p1) / x1 + (1 - p2) / x2) if x1 > 0 and x2 > 0 else float("nan")
        L.append(f"relative risk = {fmt(rr)}   CI ({fmt(rr * math.exp(-zc * s_))} , {fmt(rr * math.exp(zc * s_))})")
    if min(x1, x2, n1 - x1, n2 - x2) > 0:
        orr = x1 * (n2 - x2) / (x2 * (n1 - x1))
        s_ = math.sqrt(1 / x1 + 1 / (n1 - x1) + 1 / x2 + 1 / (n2 - x2))
        L.append(f"odds ratio = {fmt(orr)}   CI ({fmt(orr * math.exp(-zc * s_))} , {fmt(orr * math.exp(zc * s_))})")
    return "\n".join(L)


def calc_gof(v, a):
    obs = np.array(parse_list(v[0]))
    m = int(v[2])
    k = len(obs)
    if k < 2 or np.any(obs < 0):
        raise ValueError("Enter at least two non-negative observed counts.")
    pr = np.array(parse_list(v[1])) if str(v[1]).strip() else np.full(k, 1 / k)
    if len(pr) != k:
        raise ValueError("Expected probabilities must have the same length as the counts.")
    if abs(pr.sum() - 1) > 1e-6:
        if pr.sum() > 0 and abs(pr.sum() - 1) < 0.5:
            pr = pr / pr.sum()
        else:
            raise ValueError("Expected probabilities must sum to 1.")
    n = obs.sum()
    ex = n * pr
    chi = float(np.sum((obs - ex) ** 2 / ex))
    df = k - 1 - m
    if df < 1:
        raise ValueError("Degrees of freedom < 1 (too many estimated parameters).")
    p = float(stats.chi2.sf(chi, df))
    L = ["CHI-SQUARE GOODNESS-OF-FIT", "=" * 28, "H0 : the data follow the specified distribution", "",
         f"{'Cell':<6}{'Observed':>12}{'Expected':>12}{'(O−E)/√E':>12}"]
    for i in range(k):
        L.append(f"{i + 1:<6}{fmt(obs[i]):>12}{fmt(ex[i]):>12}{fmt((obs[i] - ex[i]) / math.sqrt(ex[i])):>12}")
    L += ["", f"χ² = Σ(O−E)²/E = {fmt(chi)},  df = {df},  critical value (α = {a:g}) = {fmt(float(stats.chi2.isf(a, df)))}",
          _decision(p, a)]
    if np.any(ex < 5):
        L.append(f"WARNING: {int(np.sum(ex < 5))} cell(s) have expected count < 5 - merge categories.")
    return "\n".join(L)


def calc_independence(v, a):
    rows = [parse_list(ln) for ln in str(v[0]).strip().splitlines() if ln.strip()]
    if len(rows) < 2 or len({len(r) for r in rows}) != 1 or len(rows[0]) < 2:
        raise ValueError("Enter a rectangular table (≥ 2 rows and ≥ 2 columns), one row per line.")
    t = np.array(rows)
    if np.any(t < 0):
        raise ValueError("Counts must be non-negative.")
    yates = v[1] == "yes (2×2 only)"
    chi, p, dof, ex = stats.chi2_contingency(t, correction=yates and t.shape == (2, 2))
    n = t.sum()
    V = math.sqrt(chi / (n * min(t.shape[0] - 1, t.shape[1] - 1))) if n > 0 else float("nan")
    res = (t - ex) / np.sqrt(ex)
    r_l = [f"R{i + 1}" for i in range(t.shape[0])]
    c_l = [f"C{j + 1}" for j in range(t.shape[1])]

    def mat(M, d=4):
        head = " " * 6 + "".join(f"{c:>12}" for c in c_l)
        return "\n".join([head] + [f"{r_l[i]:<6}" + "".join(f"{fmt(M[i, j], d):>12}" for j in range(M.shape[1]))
                                   for i in range(M.shape[0])])

    L = ["CHI-SQUARE TEST OF INDEPENDENCE", "=" * 34, "H0 : the row and column variables are independent", "",
         "OBSERVED", mat(t), "", "EXPECTED", mat(ex), "", "STANDARDISED RESIDUALS (|r| > 2 suggest the cell drives dependence)",
         mat(res), "",
         f"χ² = {fmt(chi)},  df = {dof},  n = {int(n)},  Cramér's V = {fmt(V)}", _decision(float(p), a)]
    if t.shape == (2, 2):
        fe = stats.fisher_exact(t)
        L.append(f"Fisher exact (2×2): odds ratio = {fmt(float(fe.statistic))},  {_decision(float(fe.pvalue), a)}")
    if np.any(ex < 5):
        L.append(f"WARNING: {int(np.sum(ex < 5))} cell(s) with expected count < 5 - the χ² approximation may be poor.")
    return "\n".join(L)


def calc_poisson(v, a):
    c, T, lam0, alt = int(v[0]), v[1], v[2], v[3]
    if c < 0 or T <= 0:
        raise ValueError("Need count ≥ 0 and exposure > 0.")
    lo = stats.chi2.ppf(a / 2, 2 * c) / (2 * T) if c > 0 else 0.0
    hi = stats.chi2.ppf(1 - a / 2, 2 * c + 2) / (2 * T)
    L = ["POISSON RATE", "=" * 14, f"events c = {c}, exposure T = {fmt(T)},  rate λ̂ = c/T = {fmt(c / T)}",
         f"exact {(1 - a) * 100:g}% CI for λ: ({fmt(lo)} , {fmt(hi)})"]
    if lam0 is not None:
        mu = lam0 * T
        p = _tail_p(stats.poisson.cdf(c, mu), stats.poisson.sf(c - 1, mu), alt)
        L += ["", f"H0 : λ = {fmt(lam0)}   (H1: {alt}),  expected count under H0 = {fmt(mu)}", _decision(p, a)]
    return "\n".join(L)


def calc_t_one(v, a):
    n, m, s, mu0, alt = int(v[0]), v[1], v[2], v[3], v[4]
    if n < 2 or s <= 0:
        raise ValueError("Need n ≥ 2 and s > 0.")
    se = s / math.sqrt(n)
    t = (m - mu0) / se
    df = n - 1
    p = _tail_p(stats.t.cdf(t, df), stats.t.sf(t, df), alt)
    tc = stats.t.ppf(1 - a / 2, df)
    return "\n".join(["ONE-SAMPLE t-TEST (summary data)", "=" * 32] + _h_lines("", alt, "μ", fmt(mu0)) +
                     ["", f"SE = {fmt(se)},  t = {fmt(t)},  df = {df}",
                      f"{(1 - a) * 100:g}% CI for μ: ({fmt(m - tc * se)} , {fmt(m + tc * se)})",
                      f"Cohen's d = {fmt((m - mu0) / s)}", _decision(p, a)])


def calc_t_two(v, a):
    n1, m1, s1, n2, m2, s2, kind, alt = int(v[0]), v[1], v[2], int(v[3]), v[4], v[5], v[6], v[7]
    if min(n1, n2) < 2 or s1 <= 0 or s2 <= 0:
        raise ValueError("Need n ≥ 2 and s > 0 in both samples.")
    d = m1 - m2
    if kind.startswith("Welch"):
        se = math.sqrt(s1 ** 2 / n1 + s2 ** 2 / n2)
        df = (s1 ** 2 / n1 + s2 ** 2 / n2) ** 2 / ((s1 ** 2 / n1) ** 2 / (n1 - 1) + (s2 ** 2 / n2) ** 2 / (n2 - 1))
    else:
        sp2 = ((n1 - 1) * s1 ** 2 + (n2 - 1) * s2 ** 2) / (n1 + n2 - 2)
        se = math.sqrt(sp2 * (1 / n1 + 1 / n2))
        df = n1 + n2 - 2
    t = d / se
    p = _tail_p(stats.t.cdf(t, df), stats.t.sf(t, df), alt)
    tc = stats.t.ppf(1 - a / 2, df)
    return "\n".join([f"TWO-SAMPLE t-TEST (summary data, {kind})", "=" * 40] + _h_lines("", alt, "μ1 − μ2", "0") +
                     ["", f"difference = {fmt(d)},  SE = {fmt(se)},  t = {fmt(t)},  df = {fmt(df)}",
                      f"{(1 - a) * 100:g}% CI for μ1 − μ2: ({fmt(d - tc * se)} , {fmt(d + tc * se)})", _decision(p, a)])


def calc_ci_z(v, a):
    n, m, sg = int(v[0]), v[1], v[2]
    if n < 1 or sg <= 0:
        raise ValueError("Need n ≥ 1 and σ > 0.")
    z = stats.norm.ppf(1 - a / 2)
    h = z * sg / math.sqrt(n)
    return (f"CI FOR THE MEAN (σ known)\n{'=' * 26}\nz = {fmt(z)},  margin of error = {fmt(h)}\n"
            f"{(1 - a) * 100:g}% CI: ({fmt(m - h)} , {fmt(m + h)})")


def calc_anova_summary(v, a):
    rows = [parse_list(ln) for ln in str(v[0]).strip().splitlines() if ln.strip()]
    if len(rows) < 2 or any(len(r) != 3 for r in rows):
        raise ValueError("Enter one line per group:  n, mean, sd")
    ns = np.array([r[0] for r in rows])
    ms = np.array([r[1] for r in rows])
    ss = np.array([r[2] for r in rows])
    if np.any(ns < 2) or np.any(ss <= 0):
        raise ValueError("Each group needs n ≥ 2 and sd > 0.")
    N, g = ns.sum(), len(rows)
    gm = float(np.sum(ns * ms) / N)
    ssb = float(np.sum(ns * (ms - gm) ** 2))
    ssw = float(np.sum((ns - 1) * ss ** 2))
    dfb, dfw = g - 1, int(N - g)
    F_ = (ssb / dfb) / (ssw / dfw)
    p = float(stats.f.sf(F_, dfb, dfw))
    return "\n".join(["ONE-WAY ANOVA (summary data)", "=" * 30,
                      f"{'Source':<10}{'SS':>14}{'df':>6}{'MS':>14}{'F':>10}{'p':>12}",
                      f"{'Between':<10}{fmt(ssb):>14}{dfb:>6}{fmt(ssb / dfb):>14}{fmt(F_):>10}{fmt_p(p):>12}",
                      f"{'Within':<10}{fmt(ssw):>14}{dfw:>6}{fmt(ssw / dfw):>14}",
                      f"{'Total':<10}{fmt(ssb + ssw):>14}{dfb + dfw:>6}", f"eta² = {fmt(ssb / (ssb + ssw))}",
                      _decision(p, a), f"Hartley max/min variance ratio = {fmt(float(ss.max() ** 2 / ss.min() ** 2))} (≈ 1 supports equal variances)"])


def calc_corr_test(v, a):
    r, n, rho0 = v[0], int(v[1]), v[2]
    if not -1 < r < 1 or n < 4:
        raise ValueError("Need −1 < r < 1 and n ≥ 4.")
    t = r * math.sqrt((n - 2) / (1 - r * r))
    p_t = 2 * stats.t.sf(abs(t), n - 2)
    z = math.atanh(r)
    se = 1 / math.sqrt(n - 3)
    zc = stats.norm.ppf(1 - a / 2)
    zt = (z - math.atanh(rho0)) / se
    return "\n".join(["CORRELATION TEST", "=" * 18,
                      f"r = {fmt(r)}, n = {n}, R² = {fmt(r * r)}", "",
                      f"H0: ρ = 0   t = {fmt(t)}, df = {n - 2}   {_decision(float(p_t), a)}",
                      f"H0: ρ = {fmt(rho0)} (Fisher z)   z = {fmt(zt)}   {_decision(float(2 * stats.norm.sf(abs(zt))), a)}",
                      f"{(1 - a) * 100:g}% CI for ρ: ({fmt(math.tanh(z - zc * se))} , {fmt(math.tanh(z + zc * se))})"])


def calc_n_mean(v, a):
    sg, E = v[0], v[1]
    if sg <= 0 or E <= 0:
        raise ValueError("σ and E must be > 0.")
    z = stats.norm.ppf(1 - a / 2)
    n0 = (z * sg / E) ** 2
    n = max(2, math.ceil(n0))
    for _ in range(100):
        nn = max(2, math.ceil((stats.t.ppf(1 - a / 2, n - 1) * sg / E) ** 2))
        if nn == n:
            break
        n = nn
    return (f"SAMPLE SIZE FOR ESTIMATING A MEAN\n{'=' * 34}\nσ = {fmt(sg)}, margin of error E = {fmt(E)}, "
            f"confidence {(1 - a) * 100:g}%\nz-based: n = (zσ/E)² = {fmt(n0)}  ->  n = {math.ceil(n0)}\n"
            f"t-based (σ replaced by s): n = {n}")


def calc_n_prop(v, a):
    p, E = v[0], v[1]
    if not 0 < p < 1 or E <= 0:
        raise ValueError("Need 0 < p < 1 and E > 0 (use p = 0.5 if unknown).")
    z = stats.norm.ppf(1 - a / 2)
    return (f"SAMPLE SIZE FOR ESTIMATING A PROPORTION\n{'=' * 40}\nplanning p = {fmt(p)}, margin E = {fmt(E)}, "
            f"confidence {(1 - a) * 100:g}%\nn = z²·p·(1−p)/E² = {fmt(z * z * p * (1 - p) / E ** 2)}  ->  n = {math.ceil(z * z * p * (1 - p) / E ** 2)}\n"
            f"worst case (p = 0.5): n = {math.ceil(z * z * 0.25 / E ** 2)}")


def t_power(d, n, a, design, alt):
    df = n - 1 if design.startswith("one") else 2 * n - 2
    delta = d * math.sqrt(n) if design.startswith("one") else d * math.sqrt(n / 2)
    if alt == "two-sided":
        tc = stats.t.ppf(1 - a / 2, df)
        return float(stats.nct.sf(tc, df, delta) + stats.nct.cdf(-tc, df, delta))
    return float(stats.nct.sf(stats.t.ppf(1 - a, df), df, delta))


def calc_power_t(v, a):
    design, d, n, target, alt = v[0], v[1], v[2], v[3], v[4]
    if d <= 0:
        raise ValueError("Effect size d must be > 0 (d = difference / σ).")
    L = ["POWER ANALYSIS FOR THE t-TEST", "=" * 30, f"design: {design},  d = {fmt(d)},  α = {a:g},  {alt}"]
    if n is not None:
        L.append(f"n = {int(n)}{' per group' if design.startswith('two') else ''}  ->  power = {fmt(t_power(d, int(n), a, design, alt))}")
    if target is not None:
        if not 0 < target < 1:
            raise ValueError("Target power must be in (0, 1).")
        nn = 2
        while nn < 100000 and t_power(d, nn, a, design, alt) < target:
            nn += 1
        L.append(f"required n for power {fmt(target)}: {nn}{' per group' if design.startswith('two') else ''}"
                 f"  (achieved power {fmt(t_power(d, nn, a, design, alt))})")
    L.append("Cohen's guide for d: 0.2 small, 0.5 medium, 0.8 large.")
    return "\n".join(L)


def calc_power_prop(v, a):
    p1, p2, n, target = v
    if not (0 < p1 < 1 and 0 < p2 < 1) or p1 == p2:
        raise ValueError("Need p1 ≠ p2, both in (0, 1).")
    za = stats.norm.ppf(1 - a / 2)
    pb = (p1 + p2) / 2
    L = ["POWER FOR COMPARING TWO PROPORTIONS (normal approx., two-sided)", "=" * 56, f"p1 = {fmt(p1)}, p2 = {fmt(p2)}, α = {a:g}"]
    if n is not None:
        zb = (abs(p1 - p2) * math.sqrt(n) - za * math.sqrt(2 * pb * (1 - pb))) / math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
        L.append(f"n = {int(n)} per group  ->  power = {fmt(float(stats.norm.cdf(zb)))}")
    if target is not None:
        zb = stats.norm.ppf(target)
        nn = (za * math.sqrt(2 * pb * (1 - pb)) + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2 / (p1 - p2) ** 2
        L.append(f"required n for power {fmt(target)}: {math.ceil(nn)} per group")
    return "\n".join(L)


def calc_tol(v, a):
    n, m, s, cov = int(v[0]), v[1], v[2], v[3]
    if n < 2 or s <= 0 or not 0 < cov < 1:
        raise ValueError("Need n ≥ 2, s > 0 and 0 < coverage < 1.")
    k = tolerance_k(n, cov, 1 - a)
    tc = stats.t.ppf(1 - a / 2, n - 1)
    pi = tc * s * math.sqrt(1 + 1 / n)
    return "\n".join(["NORMAL TOLERANCE & PREDICTION INTERVALS", "=" * 42,
                      f"n = {n}, mean = {fmt(m)}, s = {fmt(s)}", "",
                      f"tolerance interval containing {cov * 100:g}% of the population with {(1 - a) * 100:g}% confidence:",
                      f"  k = {fmt(k)}   ->   ({fmt(m - k * s)} , {fmt(m + k * s)})",
                      f"{(1 - a) * 100:g}% prediction interval for one future observation: ({fmt(m - pi)} , {fmt(m + pi)})"])


def calc_comb(v, a):
    n, r = int(v[0]), int(v[1])
    if n < 0 or r < 0 or n > 100000:
        raise ValueError("Need 0 ≤ n ≤ 100000 and r ≥ 0.")
    L = ["COMBINATORICS", "=" * 14, f"n! = {math.factorial(n) if n <= 200 else 'too large to print'}"]
    if r <= n:
        L += [f"P(n, r) = n!/(n−r)!           = {math.perm(n, r)}", f"C(n, r) = n!/(r!(n−r)!)        = {math.comb(n, r)}"]
    else:
        L.append("(r > n: no arrangements without repetition)")
    L += [f"n^r  (ordered, with repetition) = {n ** r if r <= 400 else 'too large to print'}",
          f"C(n+r−1, r)  (unordered, with repetition) = {math.comb(n + r - 1, r) if n + r - 1 >= 0 else 0}"]
    return "\n".join(L)


def calc_bayes(v, a):
    pri, lik = parse_list(v[0]), parse_list(v[1])
    names = [t for t in re.split(r"[,;]+", str(v[2])) if t.strip()] if str(v[2]).strip() else []
    if len(pri) != len(lik) or len(pri) < 2:
        raise ValueError("Priors and likelihoods need the same length (≥ 2).")
    if any(p < 0 or p > 1 for p in pri + lik) or abs(sum(pri) - 1) > 1e-6:
        raise ValueError("Priors must be probabilities summing to 1; likelihoods must be in [0, 1].")
    tot = sum(p * l for p, l in zip(pri, lik))
    if tot == 0:
        raise ValueError("P(evidence) = 0: posterior undefined.")
    L = ["BAYES' THEOREM", "=" * 16, f"P(E) = Σ P(E|Hi)·P(Hi) = {fmt(tot)}  (law of total probability)", "",
         f"{'Hypothesis':<14}{'Prior P(Hi)':>14}{'P(E|Hi)':>12}{'Joint':>12}{'Posterior P(Hi|E)':>20}"]
    for i, (p, l) in enumerate(zip(pri, lik)):
        nm = names[i].strip() if i < len(names) else f"H{i + 1}"
        L.append(f"{nm[:13]:<14}{fmt(p):>14}{fmt(l):>12}{fmt(p * l):>12}{fmt(p * l / tot):>20}")
    return "\n".join(L)


def calc_events(v, a):
    pa, pb, given, val = v[0], v[1], v[2], v[3]
    if not (0 <= pa <= 1 and 0 <= pb <= 1):
        raise ValueError("P(A) and P(B) must be in [0, 1].")
    if given == "independent":
        pab = pa * pb
    else:
        if val is None:
            raise ValueError("Enter the value in the last field.")
        pab = val if given == "P(A∩B)" else pa + pb - val
    lo, hi = max(0.0, pa + pb - 1), min(pa, pb)
    if pab < lo - 1e-12 or pab > hi + 1e-12:
        raise ValueError(f"Inconsistent inputs: P(A∩B) must lie in [{fmt(lo)}, {fmt(hi)}].")
    L = ["EVENT PROBABILITIES", "=" * 20, f"P(A) = {fmt(pa)},  P(B) = {fmt(pb)},  P(A∩B) = {fmt(pab)}",
         f"P(A∪B) = P(A)+P(B)−P(A∩B) = {fmt(pa + pb - pab)}", f"P(A') = {fmt(1 - pa)},  P(B') = {fmt(1 - pb)}",
         f"P(neither) = {fmt(1 - (pa + pb - pab))},  P(A only) = {fmt(pa - pab)},  P(B only) = {fmt(pb - pab)}"]
    if pb > 0:
        L.append(f"P(A|B) = P(A∩B)/P(B) = {fmt(pab / pb)}")
    if pa > 0:
        L.append(f"P(B|A) = P(A∩B)/P(A) = {fmt(pab / pa)}")
    L.append("independent: " + ("YES (P(A∩B) = P(A)P(B))" if abs(pab - pa * pb) < 1e-9 else f"NO (P(A)P(B) = {fmt(pa * pb)})")
             + ";   mutually exclusive: " + ("YES" if abs(pab) < 1e-12 else "NO"))
    return "\n".join(L)


def calc_pmf(v, a):
    x, p = parse_list(v[0]), parse_list(v[1])
    if len(x) != len(p) or len(x) < 2:
        raise ValueError("x and p lists must have the same length (≥ 2).")
    if any(q < 0 for q in p):
        raise ValueError("Probabilities must be ≥ 0.")
    s = sum(p)
    L = ["CUSTOM DISCRETE DISTRIBUTION", "=" * 30]
    if abs(s - 1) > 1e-6:
        L.append(f"WARNING: probabilities sum to {fmt(s)}, not 1 - they were normalised.")
        p = [q / s for q in p]
    order = np.argsort(x)
    xs, ps = np.array(x)[order], np.array(p)[order]
    cdf = np.cumsum(ps)
    mean = float(np.sum(xs * ps))
    ex2 = float(np.sum(xs ** 2 * ps))
    var = ex2 - mean ** 2
    sd = math.sqrt(max(var, 0))
    L += [f"E[X] = {fmt(mean)},  E[X²] = {fmt(ex2)},  Var(X) = {fmt(var)},  σ = {fmt(sd)}",
          f"mode = {', '.join(fmt(float(t)) for t in xs[ps == ps.max()])},  median = {fmt(float(xs[np.searchsorted(cdf, 0.5 - 1e-12)]))}"]
    if sd > 0:
        L.append(f"skewness = {fmt(float(np.sum(((xs - mean) / sd) ** 3 * ps)))}")
    L += ["", f"{'x':>12}{'P(X=x)':>14}{'P(X≤x)':>14}"] + [f"{fmt(float(a_)):>12}{fmt(float(b_)):>14}{fmt(float(c_)):>14}" for a_, b_, c_ in zip(xs, ps, cdf)]
    return "\n".join(L)


def calc_cheb(v, a):
    mu, sg, k, a0 = v
    if sg <= 0 or k <= 0:
        raise ValueError("Need σ > 0 and k > 0.")
    L = ["CHEBYSHEV & MARKOV BOUNDS", "=" * 28, f"μ = {fmt(mu)}, σ = {fmt(sg)}, k = {fmt(k)}",
         f"Chebyshev: P(|X − μ| ≥ kσ) ≤ 1/k² = {fmt(min(1.0, 1 / k ** 2))}",
         f"           P(μ − kσ < X < μ + kσ) ≥ {fmt(max(0.0, 1 - 1 / k ** 2))}  (any distribution)",
         f"Normal:    P(|X − μ| < kσ) = {fmt(float(2 * stats.norm.cdf(k) - 1))}  (for comparison, if X is normal)"]
    if a0 is not None and a0 > 0 and mu >= 0:
        L.append(f"Markov (X ≥ 0): P(X ≥ {fmt(a0)}) ≤ μ/a = {fmt(min(1.0, mu / a0))}")
    return "\n".join(L)


def calc_lincomb(v, a):
    ca, cb, mx, my, sx, sy, rho = v
    if sx < 0 or sy < 0 or not -1 <= rho <= 1:
        raise ValueError("Need σ ≥ 0 and −1 ≤ ρ ≤ 1.")
    cov = rho * sx * sy
    var = ca ** 2 * sx ** 2 + cb ** 2 * sy ** 2 + 2 * ca * cb * cov
    return "\n".join(["LINEAR COMBINATION  W = aX + bY", "=" * 34,
                      f"E[W] = aμX + bμY = {fmt(ca * mx + cb * my)}", f"Cov(X,Y) = ρσXσY = {fmt(cov)}",
                      f"Var(W) = a²σX² + b²σY² + 2ab·Cov = {fmt(var)},  σW = {fmt(math.sqrt(max(var, 0)))}",
                      f"(X+Y): Var = {fmt(sx ** 2 + sy ** 2 + 2 * cov)};   (X−Y): Var = {fmt(sx ** 2 + sy ** 2 - 2 * cov)}"])


def calc_sampling(v, a):
    mu, sg, n, x1, x2, N = v[0], v[1], int(v[2]), v[3], v[4], v[5]
    if sg <= 0 or n < 1:
        raise ValueError("Need σ > 0 and n ≥ 1.")
    se = sg / math.sqrt(n)
    fpc = ""
    if N is not None and N > n:
        se *= math.sqrt((N - n) / (N - 1))
        fpc = f"  (finite-population correction applied, N = {int(N)})"
    L = ["SAMPLING DISTRIBUTION OF THE SAMPLE MEAN", "=" * 42, f"E[X̄] = {fmt(mu)},  SE = σ/√n = {fmt(se)}{fpc}",
         "X̄ ~ N(μ, SE²) exactly if the population is normal, approximately (CLT) otherwise for large n."]
    if x1 is not None:
        L += [f"P(X̄ ≤ {fmt(x1)}) = {fmt(float(stats.norm.cdf(x1, mu, se)))},   P(X̄ ≥ {fmt(x1)}) = {fmt(float(stats.norm.sf(x1, mu, se)))}",
              f"z = {fmt((x1 - mu) / se)}"]
    if x1 is not None and x2 is not None:
        lo, hi = min(x1, x2), max(x1, x2)
        L.append(f"P({fmt(lo)} < X̄ < {fmt(hi)}) = {fmt(float(stats.norm.cdf(hi, mu, se) - stats.norm.cdf(lo, mu, se)))}")
    return "\n".join(L)


def calc_normal_binom(v, a):
    n, p, k = int(v[0]), v[1], int(v[2])
    if n < 1 or not 0 < p < 1 or not 0 <= k <= n:
        raise ValueError("Need n ≥ 1, 0 < p < 1 and 0 ≤ k ≤ n.")
    mu, sd = n * p, math.sqrt(n * p * (1 - p))
    ex = float(stats.binom.cdf(k, n, p))
    ap = float(stats.norm.cdf((k + 0.5 - mu) / sd))
    L = ["NORMAL APPROXIMATION TO THE BINOMIAL", "=" * 38, f"X ~ Bin({n}, {fmt(p)}),  μ = np = {fmt(mu)},  σ = √(npq) = {fmt(sd)}",
         f"P(X ≤ {k}):  exact = {fmt(ex)},  normal with continuity correction = {fmt(ap)},  without = {fmt(float(stats.norm.cdf((k - mu) / sd)))}",
         f"P(X = {k}):  exact = {fmt(float(stats.binom.pmf(k, n, p)))},  normal = {fmt(float(stats.norm.cdf((k + .5 - mu) / sd) - stats.norm.cdf((k - .5 - mu) / sd)))}",
         f"absolute error (with correction) = {fmt(abs(ex - ap))}"]
    L.append("Rule of thumb satisfied (np ≥ 5 and nq ≥ 5)." if n * p >= 5 and n * (1 - p) >= 5 else
             "WARNING: np or nq < 5 - the normal approximation is unreliable here.")
    if n >= 20 and p <= 0.05:
        L.append(f"Poisson approximation Po(np): P(X ≤ {k}) = {fmt(float(stats.poisson.cdf(k, mu)))}")
    return "\n".join(L)


def calc_system(v, a):
    r = parse_list(v[0])
    k = int(v[1])
    if not r or any(q < 0 or q > 1 for q in r):
        raise ValueError("Component reliabilities must be probabilities in [0, 1].")
    n = len(r)
    if not 1 <= k <= n:
        raise ValueError(f"k must be between 1 and {n}.")
    dist = np.zeros(n + 1)
    dist[0] = 1.0
    for q in r:
        new = np.zeros(n + 1)
        new[:-1] += dist[:-1] * (1 - q)
        new[1:] += dist[:-1] * q
        dist = new
    return "\n".join(["SYSTEM RELIABILITY (independent components)", "=" * 44, f"n = {n} components: {', '.join(fmt(q) for q in r)}",
                      f"series (all must work)     R = ∏Ri = {fmt(float(np.prod(r)))}",
                      f"parallel (any one works)   R = 1 − ∏(1−Ri) = {fmt(float(1 - np.prod(1 - np.array(r))))}",
                      f"{k}-out-of-{n} (≥ {k} work)     R = {fmt(float(dist[k:].sum()))}"])


def calc_exp_rel(v, a):
    mtbf, t, target = v
    if mtbf <= 0:
        raise ValueError("MTBF must be > 0.")
    lam = 1 / mtbf
    L = ["EXPONENTIAL RELIABILITY", "=" * 24, f"MTBF = {fmt(mtbf)},  λ = 1/MTBF = {fmt(lam)}"]
    if t is not None:
        L += [f"R({fmt(t)}) = exp(−λt) = {fmt(math.exp(-lam * t))},   F(t) = {fmt(1 - math.exp(-lam * t))}",
              f"memoryless property: P(survive t | already survived s) = R(t);  3 identical units in series: R = {fmt(math.exp(-3 * lam * t))}"]
    if target is not None:
        if not 0 < target < 1:
            raise ValueError("Target reliability must be in (0, 1).")
        L.append(f"time for reliability {fmt(target)}: t = −MTBF·ln(R) = {fmt(-mtbf * math.log(target))}")
    return "\n".join(L)


ALT3 = ["two-sided", "less", "greater"]
_N = lambda lab="Sample size n", d="30", fill="n": F(lab, d, "i", None, fill)
CALCS = {
    "Proportions & counts": {
        "Proportion CI (x of n)": CalcSpec([F("Successes x", 7, "i"), F("Trials n", 20, "i")],
                                           "Five interval methods side by side. Confidence level = 1 − α (top bar).", calc_prop_ci),
        "One-proportion test": CalcSpec([F("Successes x", 18, "i"), F("Trials n", 40, "i"), F("Hypothesised p0", 0.5), F("Alternative", "two-sided", "c", ALT3)],
                                        "Exact binomial and normal-approximation tests.", calc_prop_test),
        "Two-proportion test": CalcSpec([F("x1", 45, "i"), F("n1", 100, "i"), F("x2", 30, "i"), F("n2", 100, "i"), F("Alternative", "two-sided", "c", ALT3)],
                                        "z-test, Fisher exact, difference CI, relative risk, odds ratio.", calc_two_prop),
        "Chi-square goodness-of-fit": CalcSpec([F("Observed counts (list)", "18, 22, 25, 35", "s"), F("Expected probabilities (blank = equal)", "", "s"),
                                                F("Parameters estimated from data", 0, "i")],
                                               "Tests whether counts match the stated cell probabilities.", calc_gof),
        "Chi-square independence (table)": CalcSpec([F("Contingency table (one row per line)", "20 15 30\n25 30 10", "m"),
                                                     F("Yates correction", "no", "c", ["no", "yes (2×2 only)"])],
                                                    "Rows/columns of counts. Also Cramér's V, residuals, Fisher exact for 2×2.", calc_independence),
        "Poisson rate (count / exposure)": CalcSpec([F("Events c", 12, "i"), F("Exposure T (time, area...)", 4), F("Hypothesised rate λ0 (optional)", "", "o"),
                                                     F("Alternative", "two-sided", "c", ALT3)], "Exact CI and test for a Poisson rate.", calc_poisson),
    },
    "Means & variances (summary data)": {
        "One-sample t-test": CalcSpec([_N(), F("Sample mean", 10.2, "f", None, "mean"), F("Sample std dev s", 1.1, "f", None, "sd"),
                                       F("Hypothesised μ0", 10), F("Alternative", "two-sided", "c", ALT3)],
                                      "Use the button below to fill n, mean, s from variable X.", calc_t_one),
        "Two-sample t-test": CalcSpec([_N("n1", "30", "n"), F("mean 1", 10.2, "f", None, "mean"), F("s1", 1.1, "f", None, "sd"),
                                       F("n2", 30, "i", None, "n2"), F("mean 2", 9.8, "f", None, "mean2"), F("s2", 1.3, "f", None, "sd2"),
                                       F("Variances", "Welch (unequal variances)", "c", ["Welch (unequal variances)", "pooled (equal variances)"]),
                                       F("Alternative", "two-sided", "c", ALT3)], "Fill buttons use X for sample 1 and Y for sample 2.", calc_t_two),
        "CI for mean (σ known)": CalcSpec([_N(), F("Sample mean", 10.2, "f", None, "mean"), F("Known σ", 1.0)], "z-interval.", calc_ci_z),
        "One-way ANOVA from summary": CalcSpec([F("Groups: n, mean, sd (one line each)", "10, 5.1, 0.8\n12, 5.9, 0.9\n11, 6.4, 0.7", "m")],
                                               "Group summary lines.", calc_anova_summary),
        "Correlation test (r, n)": CalcSpec([F("Sample correlation r", 0.62), F("n", 25, "i"), F("Hypothesised ρ0", 0)], "t-test for ρ = 0, Fisher z for others.", calc_corr_test),
        "Tolerance & prediction interval": CalcSpec([_N(), F("Sample mean", 10.2, "f", None, "mean"), F("Sample std dev s", 1.1, "f", None, "sd"),
                                                     F("Population coverage", 0.95)], "Normal data. Confidence = 1 − α (top bar).", calc_tol),
    },
    "Sample size & power": {
        "n to estimate a mean": CalcSpec([F("σ (planning value)", 2.0), F("Margin of error E", 0.5)], "Confidence = 1 − α.", calc_n_mean),
        "n to estimate a proportion": CalcSpec([F("Planning p", 0.5), F("Margin of error E", 0.03)], "Use p = 0.5 when unknown (worst case).", calc_n_prop),
        "Power / n for t-test": CalcSpec([F("Design", "two-sample (n per group)", "c", ["one-sample / paired", "two-sample (n per group)"]),
                                          F("Effect size d = Δ/σ", 0.5), F("n (blank to solve)", "", "o"), F("Target power (blank to skip)", 0.8, "o"),
                                          F("Alternative", "two-sided", "c", ["two-sided", "one-sided"])],
                                         "Noncentral-t power. Fill n to get power, or the target power to get n.", calc_power_t),
        "Power / n for two proportions": CalcSpec([F("p1", 0.40), F("p2", 0.55), F("n per group (blank to solve)", "", "o"), F("Target power (blank to skip)", 0.8, "o")],
                                                  "Normal approximation, two-sided α.", calc_power_prop),
    },
    "Probability rules": {
        "Combinatorics": CalcSpec([F("n", 10, "i"), F("r", 3, "i")], "Permutations, combinations, with/without repetition.", calc_comb),
        "Bayes' theorem": CalcSpec([F("Priors P(Hi) (list)", "0.01, 0.99", "s"), F("Likelihoods P(E|Hi) (list)", "0.95, 0.05", "s"), F("Labels (optional)", "disease, healthy", "s")],
                                   "Total probability and posterior probabilities.", calc_bayes),
        "Two events A, B": CalcSpec([F("P(A)", 0.5), F("P(B)", 0.4), F("Given", "P(A∩B)", "c", ["P(A∩B)", "P(A∪B)", "independent"]), F("Value (if needed)", 0.2, "o")],
                                    "Union, conditional probabilities, independence check.", calc_events),
        "Custom discrete distribution": CalcSpec([F("Values x (list)", "0, 1, 2, 3", "s"), F("Probabilities (list)", "0.1, 0.3, 0.4, 0.2", "s")],
                                                 "E[X], Var, CDF table from your own PMF.", calc_pmf),
        "Chebyshev & Markov": CalcSpec([F("Mean μ", 50), F("Std dev σ", 5), F("k", 2), F("Markov threshold a (optional)", "", "o")], "Distribution-free bounds.", calc_cheb),
        "Linear combination aX + bY": CalcSpec([F("a", 1), F("b", 1), F("μX", 10), F("μY", 20), F("σX", 2), F("σY", 3), F("Correlation ρ", 0)],
                                               "Mean and variance of aX + bY.", calc_lincomb),
        "Sampling distribution of X̄": CalcSpec([F("Population mean μ", 50), F("Population σ", 10), _N("Sample size n", "25", None),
                                                 F("x1 (optional)", 52, "o"), F("x2 (optional)", "", "o"), F("Population size N (optional)", "", "o")],
                                                "Central limit theorem probabilities for the sample mean.", calc_sampling),
        "Normal approx. to binomial": CalcSpec([F("n", 50, "i"), F("p", 0.4), F("k", 24, "i")], "Continuity-corrected comparison with the exact result.", calc_normal_binom),
    },
    "Reliability": {
        "Series / parallel / k-of-n": CalcSpec([F("Component reliabilities (list)", "0.95, 0.9, 0.99", "s"), F("k (for k-out-of-n)", 2, "i")],
                                               "Independent components.", calc_system),
        "Exponential model (MTBF)": CalcSpec([F("MTBF", 1000), F("Mission time t (optional)", 100, "o"), F("Target reliability (optional)", 0.9, "o")],
                                             "Constant failure rate.", calc_exp_rel),
    },
}


# ============================================================================
# EXTRA GUI TABS  (mixin used by StatLab)
# ============================================================================
EXTRA_TESTS = ("Runs test (randomness about the median)", "Sign test (median)", "Kolmogorov-Smirnov (two samples)",
               "Levene / Brown-Forsythe (all columns)", "Bartlett (all columns)", "Tukey HSD post-hoc (all columns)")
CC_KINDS = ["I-MR (individuals)", "X̄-R (consecutive subgroups)", "X̄-S (consecutive subgroups)",
            "X̄-R (each row = subgroup, all columns)", "X̄-S (each row = subgroup, all columns)"]


class ExtraTabs:
    # ------------------------------------------------------------- shared
    def grid_entries(self, parent, items):
        self.grid_entries_at(parent, 0, items)

    def grid_entries_at(self, parent, start, items):
        for i, (lab, var, w) in enumerate(items, start=start):
            ttk.Label(parent, text=lab, style="Dim.TLabel").grid(row=i, column=0, sticky="w", pady=3, padx=(0, 8))
            ttk.Entry(parent, textvariable=var, width=w).grid(row=i, column=1, sticky="w", pady=3)

    def inner_nb(self, parent):
        nb = ttk.Notebook(parent, style="Inner.TNotebook")
        nb.pack(fill="both", expand=True, padx=2, pady=2)
        return nb

    def opt_float(self, s, label):
        return self.fnum(s, label) if str(s).strip() else None

    def on_new_data(self):
        """Refresh widgets of the extra tabs after data was loaded / transformed."""
        cols = list(self.df.columns) if self.df is not None else []
        self.cb_cens.configure(values=["(none)"] + cols)
        if self.v_cens.get() not in cols:
            self.v_cens.set("(none)")
        self.lb_pred.delete(0, "end")
        y = self.v_y.get()
        for i, c in enumerate(cols):
            self.lb_pred.insert("end", c)
            if c != y:
                self.lb_pred.selection_set(i)

    def refresh_after_df(self, keep_x=None):
        cols = list(self.df.columns)
        self.cb_x.configure(values=cols)
        self.cb_y.configure(values=["(none)"] + cols)
        if keep_x in cols:
            self.v_x.set(keep_x)
        elif self.v_x.get() not in cols:
            self.v_x.set(cols[0])
        if self.v_y.get() not in cols:
            self.v_y.set(next((c for c in cols if c != self.v_x.get()), "(none)"))
        self.fits, self.fits_dirty = None, True
        self.fill_preview()
        self.refresh()
        self.run_relations(silent=True)
        self.on_new_data()

    # ----------------------------------------------------------- TRANSFORM
    def _tab_transform(self):
        f = self.tabs["transform"]
        pw = ttk.PanedWindow(f, orient="horizontal")
        pw.pack(fill="both", expand=True, padx=6, pady=6)
        left = ttk.Frame(pw, width=470)
        pw.add(left, weight=0)
        self.v_tname, self.v_texpr = tk.StringVar(value="force_scaled"), tk.StringVar(value="x / mean(x)")
        self.v_tf, self.v_tfk, self.v_inplace = tk.StringVar(value=TRANSFORMS[0]), tk.StringVar(value="3"), tk.BooleanVar(value=False)
        self.v_filter = tk.StringVar(value="x > 0")
        self.undo: List[pd.DataFrame] = []
        lf = ttk.LabelFrame(left, text=" NEW COLUMN FROM EXPRESSION ")
        lf.pack(fill="x", padx=4, pady=4)
        g = ttk.Frame(lf)
        g.pack(fill="x", padx=8, pady=8)
        self.grid_entries(g, [("New column name", self.v_tname, 20), ("Expression", self.v_texpr, 38)])
        ttk.Label(lf, text="Use column names (or col[\"name\"]), x = variable X, row = row number.\nFunctions: sqrt log log10 exp "
                           "abs sin cos tan where clip mean std\nmedian min max sum cumsum diff round floor ceil sign power",
                  style="Dim.TLabel", justify="left").pack(anchor="w", padx=8)
        ttk.Button(lf, text="Add column", style="Go.TButton", command=self.tf_expr).pack(fill="x", padx=8, pady=8)
        lf = ttk.LabelFrame(left, text=" TRANSFORM VARIABLE X ")
        lf.pack(fill="x", padx=4, pady=4)
        g = ttk.Frame(lf)
        g.pack(fill="x", padx=8, pady=8)
        ttk.Combobox(g, textvariable=self.v_tf, values=TRANSFORMS, state="readonly", width=28).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(g, text="window k (moving average)", style="Dim.TLabel").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(g, textvariable=self.v_tfk, width=6).grid(row=1, column=1, sticky="w")
        ttk.Checkbutton(g, text="replace X in place (otherwise add a new column)", variable=self.v_inplace).grid(row=2, column=0, columnspan=2, sticky="w")
        ttk.Button(lf, text="Apply transform", style="Go.TButton", command=self.tf_apply).pack(fill="x", padx=8, pady=(0, 8))
        lf = ttk.LabelFrame(left, text=" CLEAN / ROWS ")
        lf.pack(fill="x", padx=4, pady=4)
        for txt, cmd in (("Drop rows with any missing value", self.tf_dropna), ("Fill missing in X with mean", lambda: self.tf_fill("mean")),
                         ("Fill missing in X with median", lambda: self.tf_fill("median")),
                         ("Set Tukey (1.5×IQR) outliers of X to missing", self.tf_outliers),
                         ("Sort rows by X (ascending)", self.tf_sort), ("Delete column X", self.tf_delcol)):
            ttk.Button(lf, text=txt, command=cmd).pack(fill="x", padx=8, pady=2)
        r = ttk.Frame(lf)
        r.pack(fill="x", padx=8, pady=6)
        ttk.Label(r, text="Keep rows where", style="Dim.TLabel").pack(side="left")
        ttk.Entry(r, textvariable=self.v_filter, width=22).pack(side="left", padx=6)
        ttk.Button(r, text="Filter", command=self.tf_filter).pack(side="left")
        r = ttk.Frame(left)
        r.pack(fill="x", padx=4, pady=6)
        for txt, cmd in (("Undo", self.tf_undo), ("Reset to original", self.tf_reset), ("Save data…", self.tf_save)):
            ttk.Button(r, text=txt, command=cmd).pack(side="left", padx=3)
        fr, self.t_tlog = self.mk_text(pw)
        pw.add(fr, weight=1)
        self.set_text(self.t_tlog, "TRANSFORM LOG\n\nEvery operation can be undone. Results appear in all other tabs "
                                   "immediately.\nExpressions are evaluated in a restricted namespace "
                                   "(no attribute access, no imports).\n")

    def tlog(self, msg):
        t = self.t_tlog
        t.config(state="normal")
        t.insert("end", "• " + msg + "\n")
        t.see("end")
        t.config(state="disabled")

    def need_data(self):
        if self.df is None:
            raise ValueError("Load data first.")

    def push_df(self, new: pd.DataFrame, msg: str, keep_x=None):
        self.undo.append(self.df.copy())
        self.undo = self.undo[-30:]
        self.df = new.reset_index(drop=True)
        self.refresh_after_df(keep_x)
        self.tlog(msg)

    def tf_guard(self, fn):
        try:
            self.need_data()
            fn()
        except Exception as e:
            messagebox.showerror("Transform", str(e))
            self.set_status(str(e), err=True)

    def unique_name(self, base):
        n, k = base, 2
        while n in self.df.columns:
            n = f"{base}_{k}"
            k += 1
        return n

    def tf_expr(self):
        def go():
            name = self.v_tname.get().strip()
            if not name:
                raise ValueError("Enter a name for the new column.")
            vals = safe_eval(self.v_texpr.get(), self.df, self.v_x.get()).astype(float)
            df = self.df.copy()
            replaced = name in df.columns
            df[name] = vals
            self.push_df(df, f"column '{name}' {'replaced' if replaced else 'added'} = {self.v_texpr.get().strip()}", keep_x=name)
        self.tf_guard(go)

    def tf_apply(self):
        def go():
            op, xn = self.v_tf.get(), self.v_x.get()
            new, info = transform_series(self.df[xn].to_numpy(float), op, int(self.fnum(self.v_tfk.get(), "window k")))
            df = self.df.copy()
            if self.v_inplace.get():
                df[xn], name = new, xn
            else:
                name = self.unique_name(f"{xn}_{re.sub(r'[^A-Za-z0-9]+', '', op.split(' (')[0])[:10]}")
                df[name] = new
            self.push_df(df, f"{op} applied to '{xn}' -> '{name}'. {info}", keep_x=name)
        self.tf_guard(go)

    def tf_dropna(self):
        def go():
            n0 = len(self.df)
            df = self.df.dropna()
            if df.empty:
                raise ValueError("Every row has a missing value - nothing would remain.")
            self.push_df(df, f"dropped {n0 - len(df)} row(s) with missing values ({len(df)} remain)")
        self.tf_guard(go)

    def tf_fill(self, how):
        def go():
            xn = self.v_x.get()
            s = self.df[xn]
            v = float(s.mean() if how == "mean" else s.median())
            df = self.df.copy()
            k = int(s.isna().sum())
            df[xn] = s.fillna(v)
            self.push_df(df, f"filled {k} missing value(s) of '{xn}' with the {how} ({fmt(v)})")
        self.tf_guard(go)

    def tf_outliers(self):
        def go():
            xn = self.v_x.get()
            s = self.df[xn]
            q1, q3 = np.nanpercentile(s, [25, 75])
            lo, hi = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
            m = (s < lo) | (s > hi)
            df = self.df.copy()
            df.loc[m, xn] = np.nan
            self.push_df(df, f"{int(m.sum())} outlier(s) of '{xn}' outside [{fmt(lo)}, {fmt(hi)}] set to missing")
        self.tf_guard(go)

    def tf_sort(self):
        def go():
            xn = self.v_x.get()
            self.push_df(self.df.sort_values(xn, kind="stable"), f"rows sorted by '{xn}' (row numbers changed)")
        self.tf_guard(go)

    def tf_delcol(self):
        def go():
            if len(self.df.columns) < 2:
                raise ValueError("Cannot delete the only column.")
            xn = self.v_x.get()
            self.push_df(self.df.drop(columns=[xn]), f"column '{xn}' deleted")
        self.tf_guard(go)

    def tf_filter(self):
        def go():
            mask = safe_eval(self.v_filter.get(), self.df, self.v_x.get()).astype(bool)
            df = self.df[mask]
            if df.empty:
                raise ValueError("The filter would remove every row.")
            self.push_df(df, f"filter '{self.v_filter.get().strip()}': kept {len(df)} of {len(mask)} rows")
        self.tf_guard(go)

    def tf_undo(self):
        if not self.undo:
            self.set_status("Nothing to undo.")
            return
        self.df = self.undo.pop()
        self.refresh_after_df()
        self.tlog("undo")

    def tf_reset(self):
        if self.df is None or self.df0 is None:
            return
        self.undo.append(self.df.copy())
        self.df = self.df0.copy()
        self.refresh_after_df()
        self.tlog("reset to the originally loaded data")

    def tf_save(self):
        if self.df is None:
            return
        p = filedialog.asksaveasfilename(title="Save current data", defaultextension=".csv",
                                         filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx")])
        if not p:
            return
        try:
            self.df.to_excel(p, index=False) if p.lower().endswith(".xlsx") else self.df.to_csv(p, index=False)
            self.set_status(f"Saved {p}")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    # ------------------------------------------------------- SPC & RELIAB.
    def _tab_spc(self):
        nb = self.inner_nb(self.tabs["spc"])
        a, b = ttk.Frame(nb), ttk.Frame(nb)
        nb.add(a, text=" CONTROL CHARTS & CAPABILITY ")
        nb.add(b, text=" WEIBULL / RELIABILITY ")
        self.v_cc, self.v_sg = tk.StringVar(value=CC_KINDS[0]), tk.StringVar(value="5")
        self.v_lsl, self.v_usl, self.v_tgt = tk.StringVar(), tk.StringVar(), tk.StringVar()
        pw = ttk.PanedWindow(a, orient="horizontal")
        pw.pack(fill="both", expand=True, padx=4, pady=4)
        left = ttk.Frame(pw, width=330)
        pw.add(left, weight=0)
        lf = ttk.LabelFrame(left, text=" CHART ")
        lf.pack(fill="x", padx=4, pady=4)
        ttk.Combobox(lf, textvariable=self.v_cc, values=CC_KINDS, state="readonly", width=36).pack(padx=8, pady=8)
        g = ttk.Frame(lf)
        g.pack(fill="x", padx=8, pady=(0, 8))
        self.grid_entries(g, [("Subgroup size n", self.v_sg, 8)])
        lf = ttk.LabelFrame(left, text=" SPECIFICATION LIMITS (optional) ")
        lf.pack(fill="x", padx=4, pady=4)
        g = ttk.Frame(lf)
        g.pack(fill="x", padx=8, pady=8)
        self.grid_entries(g, [("LSL", self.v_lsl, 12), ("USL", self.v_usl, 12), ("Target", self.v_tgt, 12)])
        ttk.Label(lf, text="With limits, Cp / Cpk / Pp / Ppk and ppm\nare computed from the chart's σ.", style="Dim.TLabel").pack(anchor="w", padx=8, pady=(0, 6))
        ttk.Button(left, text="Analyze X", style="Go.TButton", command=self.run_spc).pack(fill="x", padx=8, pady=8)
        ttk.Label(left, text="Subgroups: consecutive blocks of X, or\nevery row across all columns.", style="Dim.TLabel").pack(anchor="w", padx=8)
        right = ttk.PanedWindow(pw, orient="vertical")
        pw.add(right, weight=1)
        self.fig_spc, self.canvas_spc, holder = self.mk_figure(right)
        right.add(holder, weight=4)
        fr, self.t_spc = self.mk_text(right, height=9)
        right.add(fr, weight=2)
        self.v_cens, self.v_t0 = tk.StringVar(value="(none)"), tk.StringVar()
        pw = ttk.PanedWindow(b, orient="horizontal")
        pw.pack(fill="both", expand=True, padx=4, pady=4)
        left = ttk.Frame(pw, width=330)
        pw.add(left, weight=0)
        lf = ttk.LabelFrame(left, text=" LIFE DATA ")
        lf.pack(fill="x", padx=4, pady=4)
        ttk.Label(lf, text="Failure / survival times = variable X (all > 0)", style="Dim.TLabel").pack(anchor="w", padx=8, pady=(8, 2))
        ttk.Label(lf, text="Censoring column (1 = failure, 0 = suspended)", style="Dim.TLabel").pack(anchor="w", padx=8, pady=(6, 2))
        self.cb_cens = ttk.Combobox(lf, textvariable=self.v_cens, state="readonly", values=["(none)"], width=26)
        self.cb_cens.pack(anchor="w", padx=8)
        g = ttk.Frame(lf)
        g.pack(fill="x", padx=8, pady=8)
        self.grid_entries(g, [("Mission time t", self.v_t0, 12)])
        ttk.Button(left, text="Fit Weibull", style="Go.TButton", command=self.run_weibull).pack(fill="x", padx=8, pady=8)
        ttk.Label(left, text="Maximum-likelihood fit with right censoring,\nconfidence intervals (delta method),\n"
                             "B10 life, MTTF, R(t), hazard, and an\nexponential (MTBF) comparison.", style="Dim.TLabel", justify="left").pack(anchor="w", padx=8)
        right = ttk.PanedWindow(pw, orient="vertical")
        pw.add(right, weight=1)
        self.fig_wb, self.canvas_wb, holder = self.mk_figure(right)
        right.add(holder, weight=4)
        fr, self.t_wb = self.mk_text(right, height=9)
        right.add(fr, weight=2)

    def run_spc(self):
        try:
            self.need_data()
            kind = self.v_cc.get()
            alpha = self.alpha()
            x, _, _ = self.get_x()
            if kind.startswith("I-MR"):
                ch = control_chart("I-MR", x)
                cap = x
            else:
                ck = "Xbar-R" if kind.startswith("X̄-R") else "Xbar-S"
                if "each row" in kind:
                    ch = control_chart(ck, matrix=self.df.dropna().to_numpy(float))
                else:
                    ch = control_chart(ck, x=x, n=int(self.fnum(self.v_sg.get(), "subgroup size")))
                cap = ch["sub_x"].ravel()
            lsl, usl, tgt = (self.opt_float(v.get(), n) for v, n in ((self.v_lsl, "LSL"), (self.v_usl, "USL"), (self.v_tgt, "target")))
            txt = spc_report(ch)
            specs = None
            if lsl is not None or usl is not None:
                txt += "\n\n" + capability(cap, lsl, usl, tgt, ch["sigma"], alpha)
                specs = (lsl, usl, tgt)
            self.draw_spc(ch, cap if specs else None, specs)
            self.set_text(self.t_spc, txt)
        except Exception as e:
            self.set_text(self.t_spc, f"ERROR: {e}")
            self.set_status(str(e), err=True)

    def _cc_axis(self, ax, v, cl, ucl, lcl, title, rules):
        idx = np.arange(1, len(v) + 1)
        ax.plot(idx, v, color=ACCENT, lw=1, marker="o", ms=4)
        ax.axhline(cl, color=CYAN, lw=1.5)
        ax.axhline(ucl, color=ERR, ls="--", lw=1.2)
        if lcl > 0 or rules:
            ax.axhline(lcl, color=ERR, ls="--", lw=1.2)
        bad = set()
        if rules:
            sg = (ucl - cl) / 3
            for k in (1, 2):
                for s in (1, -1):
                    ax.axhline(cl + s * k * sg, color=DIM, ls=":", lw=0.8)
            for lst in nelson_rules(v, cl, sg).values():
                bad.update(lst)
        else:
            bad.update(np.flatnonzero((v > ucl) | (v < lcl)) + 1)
        if bad:
            b = np.array(sorted(bad))
            ax.scatter(b, v[b - 1], s=46, color=ERR, zorder=5)
        for y_, t_, c_ in ((ucl, "UCL", ERR), (cl, "CL", CYAN), (lcl, "LCL", ERR)):
            ax.annotate(f"{t_} {fmt(y_, 4)}", xy=(1, y_), xycoords=("axes fraction", "data"), ha="right", va="bottom",
                        color=c_, fontsize=8)
        self.style_ax(ax, title, None, None)

    def draw_spc(self, ch, cap, specs):
        fig = self.fig_spc
        fig.clear()
        gs = fig.add_gridspec(3 if cap is not None else 2, 1, height_ratios=[3, 2, 3] if cap is not None else [3, 2])
        a1, a2 = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
        self._cc_axis(a1, ch["vals1"], ch["cl1"], ch["ucl1"], ch["lcl1"], ch["title1"], True)
        self._cc_axis(a2, ch["vals2"], ch["cl2"], ch["ucl2"], ch["lcl2"], ch["title2"], False)
        if cap is not None:
            a3 = fig.add_subplot(gs[2])
            a3.hist(cap, bins="auto", density=True, color=ACCENT, alpha=0.5, edgecolor=BG)
            xs = np.linspace(min(cap.min(), specs[0] if specs[0] is not None else cap.min()) - cap.std(),
                             max(cap.max(), specs[1] if specs[1] is not None else cap.max()) + cap.std(), 400)
            a3.plot(xs, stats.norm.pdf(xs, cap.mean(), cap.std(ddof=1)), color=CYAN, lw=1.6, label="normal (overall)")
            for v, nm, c in ((specs[0], "LSL", ERR), (specs[1], "USL", ERR), (specs[2], "target", WARN)):
                if v is not None:
                    a3.axvline(v, color=c, lw=1.5, ls="--", label=f"{nm} = {fmt(v, 5)}")
            self.style_ax(a3, "Capability histogram", None, "density")
            self.style_legend(a3)
        self.canvas_spc.draw_idle()

    def run_weibull(self):
        try:
            self.need_data()
            xn, cn = self.v_x.get(), self.v_cens.get()
            if cn in ("(none)", ""):
                t, ev = self.df[xn].dropna().to_numpy(float), None
            else:
                if cn == xn:
                    raise ValueError("The censoring column must differ from X.")
                sub = self.df[[xn, cn]].dropna()
                t, ev = sub[xn].to_numpy(float), (sub[cn].to_numpy(float) > 0).astype(float)
            t0 = self.opt_float(self.v_t0.get(), "mission time")
            txt, res = weibull_report(t, ev, t0, self.alpha())
            self.set_text(self.t_wb, txt)
            self.draw_weibull(t, np.ones(len(t)) if ev is None else ev, res, t0)
        except Exception as e:
            self.set_text(self.t_wb, f"ERROR: {e}")
            self.set_status(str(e), err=True)

    def draw_weibull(self, t, ev, res, t0):
        fig = self.fig_wb
        fig.clear()
        b, eta = res["beta"], res["eta"]
        ax = fig.subplots(2, 2).ravel()
        ts, Fp = johnson_ranks(t, ev)
        ax[0].scatter(ts, np.log(-np.log(1 - Fp)), s=18, color=ACCENT, label="failures (Johnson/Benard ranks)")
        tt = np.geomspace(ts.min() * 0.7, ts.max() * 1.4, 200)
        ax[0].plot(tt, b * (np.log(tt) - np.log(eta)), color=CYAN, lw=1.6, label=f"β = {fmt(b, 4)}, η = {fmt(eta, 4)}")
        ax[0].set_xscale("log")
        pr = np.array([0.01, 0.05, 0.1, 0.3, 0.632, 0.9, 0.99])
        ax[0].set_yticks(np.log(-np.log(1 - pr)))
        ax[0].set_yticklabels([f"{p * 100:g}%" for p in pr])
        self.style_ax(ax[0], "Weibull probability plot", "time", "unreliability F(t)")
        self.style_legend(ax[0])
        tm = np.linspace(1e-9, max(t) * 1.4, 400)
        ax[1].plot(tm, np.exp(-(tm / eta) ** b), color=CYAN, lw=1.8)
        if t0:
            ax[1].axvline(t0, color=WARN, ls="--", lw=1)
            ax[1].scatter([t0], [math.exp(-(t0 / eta) ** b)], color=WARN, zorder=5)
        self.style_ax(ax[1], "Reliability R(t)", "time", "R(t)")
        ax[2].plot(tm, b / eta * (tm / eta) ** (b - 1), color=WARN, lw=1.8)
        self.style_ax(ax[2], "Hazard rate h(t)", "time", "h(t)")
        ax[3].hist(t[ev > 0], bins="auto", density=True, color=ACCENT, alpha=0.5, edgecolor=BG)
        ax[3].plot(tm, b / eta * (tm / eta) ** (b - 1) * np.exp(-(tm / eta) ** b), color=CYAN, lw=1.8)
        self.style_ax(ax[3], "Density f(t) vs failure times", "time", "f(t)")
        self.canvas_wb.draw_idle()

    # ------------------------------------------------------------ ADVANCED
    def _tab_adv(self):
        nb = self.inner_nb(self.tabs["adv"])
        a, b = ttk.Frame(nb), ttk.Frame(nb)
        nb.add(a, text=" MULTIPLE / POLYNOMIAL REGRESSION ")
        nb.add(b, text=" BOOTSTRAP & MONTE CARLO ")
        self.v_deg, self.v_center, self.v_mx0 = tk.StringVar(value="1"), tk.BooleanVar(value=False), tk.StringVar()
        pw = ttk.PanedWindow(a, orient="horizontal")
        pw.pack(fill="both", expand=True, padx=4, pady=4)
        left = ttk.Frame(pw, width=320)
        pw.add(left, weight=0)
        lf = ttk.LabelFrame(left, text=" MODEL:  Y (top bar) ~ predictors ")
        lf.pack(fill="both", expand=True, padx=4, pady=4)
        ttk.Label(lf, text="Predictors (Ctrl/Shift to multi-select)", style="Dim.TLabel").pack(anchor="w", padx=8, pady=(8, 2))
        self.lb_pred = tk.Listbox(lf, selectmode="extended", exportselection=False, height=8, bg=PANEL, fg=FG, selectbackground=SEL,
                                  selectforeground=ACCENT, font=self.mono, relief="flat", highlightthickness=1, highlightbackground=BORDER)
        self.lb_pred.pack(fill="both", expand=True, padx=8)
        g = ttk.Frame(lf)
        g.pack(fill="x", padx=8, pady=8)
        ttk.Label(g, text="Polynomial degree", style="Dim.TLabel").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Spinbox(g, from_=1, to=6, textvariable=self.v_deg, width=4).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Checkbutton(g, text="centre predictors (reduces VIF)", variable=self.v_center).grid(row=1, column=0, columnspan=2, sticky="w")
        ttk.Label(g, text="Predict at (one value per predictor, comma list)", style="Dim.TLabel", wraplength=280).grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Entry(g, textvariable=self.v_mx0, width=30).grid(row=3, column=0, columnspan=2, sticky="w")
        ttk.Button(lf, text="Fit model", style="Go.TButton", command=self.run_mreg).pack(fill="x", padx=8, pady=8)
        right = ttk.PanedWindow(pw, orient="vertical")
        pw.add(right, weight=1)
        self.fig_mr, self.canvas_mr, holder = self.mk_figure(right)
        right.add(holder, weight=3)
        fr, self.t_mr = self.mk_text(right, height=12)
        right.add(fr, weight=3)
        self.v_bstat, self.v_bn, self.v_bm = tk.StringVar(value="mean"), tk.StringVar(value="5000"), tk.StringVar(value="BCa")
        self.v_pn, self.v_palt = tk.StringVar(value="10000"), tk.StringVar(value="two-sided")
        self.v_cd, self.v_cp, self.v_cn, self.v_cr = tk.StringVar(value="Exponential"), tk.StringVar(), tk.StringVar(value="30"), tk.StringVar(value="5000")
        pw = ttk.PanedWindow(b, orient="horizontal")
        pw.pack(fill="both", expand=True, padx=4, pady=4)
        left = ttk.Frame(pw, width=340)
        pw.add(left, weight=0)
        lf = ttk.LabelFrame(left, text=" BOOTSTRAP CONFIDENCE INTERVAL ")
        lf.pack(fill="x", padx=4, pady=4)
        g = ttk.Frame(lf)
        g.pack(fill="x", padx=8, pady=8)
        ttk.Combobox(g, textvariable=self.v_bstat, values=BOOT_STATS, state="readonly", width=34).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(g, text="resamples", style="Dim.TLabel").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Entry(g, textvariable=self.v_bn, width=8).grid(row=1, column=1, sticky="w")
        ttk.Label(g, text="method", style="Dim.TLabel").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Combobox(g, textvariable=self.v_bm, values=["BCa", "percentile", "basic"], state="readonly", width=12).grid(row=2, column=1, sticky="w")
        ttk.Button(lf, text="Run bootstrap", style="Go.TButton", command=self.run_boot).pack(fill="x", padx=8, pady=(0, 8))
        lf = ttk.LabelFrame(left, text=" PERMUTATION TEST  X vs Y ")
        lf.pack(fill="x", padx=4, pady=4)
        g = ttk.Frame(lf)
        g.pack(fill="x", padx=8, pady=8)
        ttk.Label(g, text="resamples", style="Dim.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(g, textvariable=self.v_pn, width=8).grid(row=0, column=1, sticky="w", padx=6)
        ttk.Combobox(g, textvariable=self.v_palt, values=ALT3, state="readonly", width=10).grid(row=0, column=2, padx=6)
        ttk.Button(lf, text="Run permutation test", style="Go.TButton", command=self.run_perm).pack(fill="x", padx=8, pady=(0, 8))
        lf = ttk.LabelFrame(left, text=" CENTRAL LIMIT THEOREM DEMO ")
        lf.pack(fill="x", padx=4, pady=4)
        g = ttk.Frame(lf)
        g.pack(fill="x", padx=8, pady=8)
        ttk.Combobox(g, textvariable=self.v_cd, values=[d.name for d in DISTRIBUTIONS], state="readonly", width=24).grid(row=0, column=0, columnspan=2, sticky="w")
        self.grid_entries_at(g, 1, [("params (blank = defaults)", self.v_cp, 14), ("sample size n", self.v_cn, 8), ("simulated samples", self.v_cr, 8)])
        ttk.Button(lf, text="Simulate", style="Go.TButton", command=self.run_clt).pack(fill="x", padx=8, pady=(0, 8))
        right = ttk.PanedWindow(pw, orient="vertical")
        pw.add(right, weight=1)
        self.fig_sim, self.canvas_sim, holder = self.mk_figure(right)
        right.add(holder, weight=3)
        fr, self.t_sim = self.mk_text(right, height=9)
        right.add(fr, weight=2)

    def run_mreg(self):
        try:
            self.need_data()
            y = self.v_y.get()
            if y in ("(none)", ""):
                raise ValueError("Choose the response Y in the top bar.")
            preds = [self.lb_pred.get(i) for i in self.lb_pred.curselection()]
            x0 = parse_list(self.v_mx0.get()) if self.v_mx0.get().strip() else None
            txt, d = multi_regression(self.df, y, preds, self.alpha(), int(self.fnum(self.v_deg.get(), "degree")),
                                      bool(self.v_center.get()), x0)
            self.set_text(self.t_mr, txt)
            fig = self.fig_mr
            fig.clear()
            ax = fig.subplots(2, 2).ravel()
            ax[0].scatter(d["yhat"], d["y"], s=18, color=ACCENT)
            lim = [min(d["y"].min(), d["yhat"].min()), max(d["y"].max(), d["yhat"].max())]
            ax[0].plot(lim, lim, color=CYAN, lw=1.4)
            self.style_ax(ax[0], "Observed vs fitted", "fitted", "observed")
            ax[1].scatter(d["yhat"], d["resid"], s=18, color=ACCENT)
            ax[1].axhline(0, color=CYAN, lw=1.4)
            self.style_ax(ax[1], "Residuals vs fitted", "fitted", "residual")
            (osm, osr), (sl, ic, r) = stats.probplot(d["stud"], dist="norm")
            ax[2].scatter(osm, osr, s=16, color=ACCENT)
            ax[2].plot(osm, sl * osm + ic, color=CYAN, lw=1.4)
            self.style_ax(ax[2], "Normal Q-Q (studentized residuals)", "theoretical", "sample")
            ax[3].bar(np.arange(1, d["n"] + 1), d["cook"], color=ACCENT, width=0.8)
            ax[3].axhline(4 / d["n"], color=ERR, ls="--", lw=1.2)
            self.style_ax(ax[3], "Cook's distance (red: 4/n)", "observation", "D")
            self.canvas_mr.draw_idle()
        except Exception as e:
            self.set_text(self.t_mr, f"ERROR: {e}")
            self.set_status(str(e), err=True)

    def sim_axis(self):
        self.fig_sim.clear()
        return self.fig_sim.add_subplot(111)

    def run_boot(self):
        try:
            self.need_data()
            stat = self.v_bstat.get()
            nb_ = int(self.fnum(self.v_bn.get(), "resamples"))
            if nb_ < 200:
                raise ValueError("Use at least 200 resamples.")
            x, _, _ = self.get_x()
            y = None
            if stat in PAIRED_STATS:
                if PAIRED_STATS[stat][1]:
                    x, y, _ = self.get_xy()
                else:
                    y = clean(self.df[self.v_y.get()]) if self.v_y.get() in self.df.columns else None
            txt, dist, est, ci = bootstrap_report(x, y, stat, nb_, 1 - self.alpha(), self.v_bm.get())
            self.set_text(self.t_sim, txt)
            ax = self.sim_axis()
            ax.hist(dist, bins="auto", color=ACCENT, alpha=0.55, edgecolor=BG)
            ax.axvline(est, color=CYAN, lw=1.8, label=f"estimate {fmt(est, 5)}")
            ax.axvline(ci[0], color=WARN, ls="--", label=f"{(1 - self.alpha()) * 100:g}% CI")
            ax.axvline(ci[1], color=WARN, ls="--")
            self.style_ax(ax, f"Bootstrap distribution of the {stat}", stat, "count")
            self.style_legend(ax)
            self.canvas_sim.draw_idle()
        except Exception as e:
            self.set_text(self.t_sim, f"ERROR: {e}")
            self.set_status(str(e), err=True)

    def run_perm(self):
        try:
            self.need_data()
            if self.v_y.get() in ("(none)", ""):
                raise ValueError("Choose a Y variable in the top bar.")
            x = clean(self.df[self.v_x.get()])
            y = clean(self.df[self.v_y.get()])
            txt, null, obs = permutation_report(x, y, int(self.fnum(self.v_pn.get(), "resamples")), self.v_palt.get())
            self.set_text(self.t_sim, txt)
            ax = self.sim_axis()
            ax.hist(null, bins="auto", color=ACCENT, alpha=0.55, edgecolor=BG)
            ax.axvline(obs, color=ERR, lw=2, label=f"observed = {fmt(obs, 5)}")
            self.style_ax(ax, "Permutation null distribution (mean X − mean Y)", "difference", "count")
            self.style_legend(ax)
            self.canvas_sim.draw_idle()
        except Exception as e:
            self.set_text(self.t_sim, f"ERROR: {e}")
            self.set_status(str(e), err=True)

    def run_clt(self):
        try:
            spec = DIST_BY_NAME[self.v_cd.get()]
            params = parse_list(self.v_cp.get()) if self.v_cp.get().strip() else [v for _, v in spec.params]
            if len(params) != len(spec.params):
                raise ValueError(f"{spec.name} needs {len(spec.params)} parameter(s): " + ", ".join(l for l, _ in spec.params))
            n = int(self.fnum(self.v_cn.get(), "sample size"))
            if n < 1:
                raise ValueError("Sample size must be ≥ 1.")
            txt, means, mu, se = clt_demo(spec, params, n, int(self.fnum(self.v_cr.get(), "simulated samples")))
            self.set_text(self.t_sim, txt)
            ax = self.sim_axis()
            ax.hist(means, bins="auto", density=True, color=ACCENT, alpha=0.55, edgecolor=BG, label="simulated sample means")
            g = np.linspace(means.min(), means.max(), 400)
            ax.plot(g, stats.norm.pdf(g, mu, se), color=CYAN, lw=1.8, label="N(μ, σ²/n)  (CLT)")
            self.style_ax(ax, f"Sampling distribution of X̄  -  {spec.name}, n = {n}", "sample mean", "density")
            self.style_legend(ax)
            self.canvas_sim.draw_idle()
        except Exception as e:
            self.set_text(self.t_sim, f"ERROR: {e}")
            self.set_status(str(e), err=True)

    # ---------------------------------------------------------- CALCULATORS
    def _tab_calc(self):
        f = self.tabs["calc"]
        self.v_ccat = tk.StringVar(value=list(CALCS)[0])
        self.v_cname = tk.StringVar(value=list(CALCS[list(CALCS)[0]])[0])
        pw = ttk.PanedWindow(f, orient="horizontal")
        pw.pack(fill="both", expand=True, padx=6, pady=6)
        left = ttk.Frame(pw, width=430)
        pw.add(left, weight=0)
        lf = ttk.LabelFrame(left, text=" CALCULATOR ")
        lf.pack(fill="both", expand=True, padx=4, pady=4)
        cb = ttk.Combobox(lf, textvariable=self.v_ccat, values=list(CALCS), state="readonly", width=38)
        cb.pack(padx=8, pady=(8, 4), anchor="w")
        cb.bind("<<ComboboxSelected>>", self.calc_pick_cat)
        self.cb_cname = ttk.Combobox(lf, textvariable=self.v_cname, values=list(CALCS[self.v_ccat.get()]), state="readonly", width=38)
        self.cb_cname.pack(padx=8, pady=4, anchor="w")
        self.cb_cname.bind("<<ComboboxSelected>>", self.calc_build)
        self.lbl_chint = ttk.Label(lf, text="", style="Dim.TLabel", wraplength=390, justify="left")
        self.lbl_chint.pack(anchor="w", padx=8, pady=4)
        self.calc_form = ttk.Frame(lf)
        self.calc_form.pack(fill="both", expand=True, padx=8, pady=4)
        r = ttk.Frame(lf)
        r.pack(fill="x", padx=8, pady=8)
        ttk.Button(r, text="Calculate", style="Go.TButton", command=self.calc_run).pack(side="left", fill="x", expand=True)
        self.btn_cfill = ttk.Button(r, text="Fill n, mean, s from X / Y", command=self.calc_fill)
        self.btn_cfill.pack(side="left", padx=6)
        fr, self.t_calc = self.mk_text(pw)
        pw.add(fr, weight=1)
        self.calc_build()

    def calc_pick_cat(self, *_):
        names = list(CALCS[self.v_ccat.get()])
        self.cb_cname.configure(values=names)
        self.v_cname.set(names[0])
        self.calc_build()

    def calc_build(self, *_):
        for w in self.calc_form.winfo_children():
            w.destroy()
        spec = CALCS[self.v_ccat.get()][self.v_cname.get()]
        self.calc_widgets = []
        for i, (lab, default, kind, ch, fill) in enumerate(spec.fields):
            ttk.Label(self.calc_form, text=lab, style="Dim.TLabel", wraplength=390, justify="left").grid(row=2 * i, column=0, sticky="w", pady=(6, 0))
            if kind == "m":
                w = tk.Text(self.calc_form, height=5, width=40, bg=PANEL, fg=FG, insertbackground=ACCENT, font=self.mono, relief="flat",
                            highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT)
                w.insert("1.0", default)
                w.grid(row=2 * i + 1, column=0, sticky="we")
                self.calc_widgets.append((kind, w, lab))
            else:
                var = tk.StringVar(value=default)
                if kind == "c":
                    ttk.Combobox(self.calc_form, textvariable=var, values=ch, state="readonly", width=38).grid(row=2 * i + 1, column=0, sticky="w")
                else:
                    e = ttk.Entry(self.calc_form, textvariable=var, width=40)
                    e.grid(row=2 * i + 1, column=0, sticky="w")
                    e.bind("<Return>", lambda ev: self.calc_run())
                self.calc_widgets.append((kind, var, lab))
        self.lbl_chint.configure(text=spec.hint)
        self.btn_cfill.state(["!disabled"] if any(fd[4] for fd in spec.fields) else ["disabled"])

    def calc_values(self):
        out = []
        for kind, w, lab in self.calc_widgets:
            raw = w.get("1.0", "end").strip() if kind == "m" else w.get()
            if kind == "f":
                out.append(self.fnum(raw, lab))
            elif kind == "i":
                out.append(int(round(self.fnum(raw, lab))))
            elif kind == "o":
                out.append(self.fnum(raw, lab) if str(raw).strip() else None)
            else:
                out.append(raw)
        return out

    def calc_run(self):
        try:
            spec = CALCS[self.v_ccat.get()][self.v_cname.get()]
            txt = spec.fn(self.calc_values(), self.alpha())
            self.set_text(self.t_calc, txt)
            self.set_status(f"{self.v_cname.get()}: done")
        except Exception as e:
            self.set_text(self.t_calc, f"ERROR: {e}")
            self.set_status(str(e), err=True)

    def calc_fill(self):
        try:
            self.need_data()
            spec = CALCS[self.v_ccat.get()][self.v_cname.get()]
            x, _, _ = self.get_x()
            yv = self.v_y.get()
            y = clean(self.df[yv]) if yv in self.df.columns else None
            vals = {"n": len(x), "mean": float(x.mean()), "sd": float(x.std(ddof=1)) if len(x) > 1 else 0.0}
            if y is not None and len(y):
                vals.update(n2=len(y), mean2=float(y.mean()), sd2=float(y.std(ddof=1)) if len(y) > 1 else 0.0)
            for (kind, w, lab), fd in zip(self.calc_widgets, spec.fields):
                if fd[4] and fd[4] in vals:
                    w.set(fmt(vals[fd[4]], 10))
        except Exception as e:
            messagebox.showerror("Fill", str(e))

    # ------------------------------------------------------- extra plots
    def p_acf(self, ax):
        x, _, _ = self.get_x()
        n = len(x)
        if n < 6:
            raise ValueError("Need at least 6 observations for an autocorrelation plot.")
        m = min(40, n - 2)
        xm = x - x.mean()
        den = float(np.sum(xm ** 2))
        r = np.array([np.sum(xm[:n - k] * xm[k:]) / den for k in range(1, m + 1)])
        lags = np.arange(1, m + 1)
        ax.bar(lags, r, color=ACCENT, width=0.6)
        zc = 1.96 / math.sqrt(n)
        ax.axhline(zc, color=ERR, ls="--", lw=1)
        ax.axhline(-zc, color=ERR, ls="--", lw=1)
        ax.axhline(0, color=DIM, lw=1)
        h = min(10, m)
        q = n * (n + 2) * float(np.sum(r[:h] ** 2 / (n - lags[:h])))
        pq = float(stats.chi2.sf(q, h))
        self.style_ax(ax, f"Autocorrelation of {self.v_x.get()}   (Ljung-Box lag {h}: Q = {fmt(q, 4)}, p {_peq(pq)})", "lag", "r(k)")

    def p_lag(self, ax):
        x, _, _ = self.get_x()
        if len(x) < 4:
            raise ValueError("Need at least 4 observations.")
        ax.scatter(x[:-1], x[1:], s=20, color=ACCENT, alpha=0.8)
        r = float(np.corrcoef(x[:-1], x[1:])[0, 1])
        self.style_ax(ax, f"Lag-1 plot  (r = {fmt(r, 4)}; random data show no pattern)", "x[t]", "x[t+1]")

    def p_pp(self, ax):
        x, _, _ = self.get_x()
        n = len(x)
        xs = np.sort(x)
        emp = (np.arange(1, n + 1) - 0.5) / n
        th = stats.norm.cdf((xs - x.mean()) / x.std(ddof=1))
        ax.scatter(th, emp, s=16, color=ACCENT)
        ax.plot([0, 1], [0, 1], color=CYAN, lw=1.5)
        self.style_ax(ax, f"Normal P-P plot - {self.v_x.get()}", "theoretical cumulative probability", "empirical cumulative probability")

    def p_means(self, ax):
        cols = list(self.df.columns)
        ms, hs = [], []
        for c in cols:
            v = clean(self.df[c])
            ms.append(v.mean())
            hs.append(stats.t.ppf(1 - self.alpha() / 2, len(v) - 1) * v.std(ddof=1) / math.sqrt(len(v)) if len(v) > 1 else 0)
        ax.errorbar(range(len(cols)), ms, yerr=hs, fmt="o", color=ACCENT, ecolor=CYAN, capsize=6, lw=1.6)
        ax.set_xticks(range(len(cols)))
        ax.set_xticklabels([str(c)[:14] for c in cols], rotation=25 if len(cols) > 5 else 0)
        self.style_ax(ax, f"Means with {(1 - self.alpha()) * 100:g}% confidence intervals", None, "mean")

    def p_matrix(self, ax):
        cols = list(self.df.columns)[:6]
        k = len(cols)
        if k < 2:
            raise ValueError("The scatter matrix needs at least two numeric columns.")
        fig = self.fig_main
        fig.clear()
        axes = fig.subplots(k, k, squeeze=False)
        for i, ci in enumerate(cols):
            for j, cj in enumerate(cols):
                a = axes[i][j]
                if i == j:
                    a.hist(clean(self.df[ci]), bins="auto", color=ACCENT, alpha=0.6, edgecolor=BG)
                else:
                    sub = self.df[[cj, ci]].dropna()
                    a.scatter(sub[cj], sub[ci], s=6, color=ACCENT, alpha=0.7)
                self.style_ax(a)
                a.tick_params(labelsize=7)
                if i == k - 1:
                    a.set_xlabel(str(cj)[:12], color=FG, fontsize=8)
                if j == 0:
                    a.set_ylabel(str(ci)[:12], color=FG, fontsize=8)

    def p_hgrid(self, ax):
        cols = list(self.df.columns)[:12]
        k = len(cols)
        r_ = math.ceil(math.sqrt(k))
        c_ = math.ceil(k / r_)
        fig = self.fig_main
        fig.clear()
        axes = fig.subplots(r_, c_, squeeze=False).ravel()
        for a, c in zip(axes, cols):
            v = clean(self.df[c])
            a.hist(v, bins="auto", density=True, color=ACCENT, alpha=0.6, edgecolor=BG)
            if len(v) > 1 and np.ptp(v) > 0:
                g = np.linspace(v.min(), v.max(), 200)
                a.plot(g, stats.norm.pdf(g, v.mean(), v.std(ddof=1)), color=CYAN, lw=1.2)
            self.style_ax(a, str(c)[:20])
            a.tick_params(labelsize=7)
        for a in axes[k:]:
            a.set_visible(False)


# ----------------------------------------------------------------------------
# GUI
# ----------------------------------------------------------------------------
@dataclass
class TestMeta:
    needs_y: bool
    mu0: bool
    sigma: bool
    sigma2: bool
    hint: str


TEST_META = {
    "One-sample t-test": TestMeta(False, True, False, False, "H0: μ = μ0 for variable X (σ unknown)."),
    "One-sample z-test (σ known)": TestMeta(False, True, True, False, "H0: μ = μ0 for X; enter the known σ."),
    "Chi-square test for variance": TestMeta(False, False, True, False,
                                             "H0: σ = σ0 for X; enter σ0 in the σ field."),
    "Two-sample t-test (Welch)": TestMeta(True, True, False, False,
                                          "X vs Y independent, unequal variances. μ0 = hypothesised μ_X − μ_Y."),
    "Two-sample t-test (pooled)": TestMeta(True, True, False, False,
                                           "X vs Y independent, equal variances. μ0 = hypothesised μ_X − μ_Y."),
    "Two-sample z-test (σ known)": TestMeta(True, True, True, True,
                                            "X vs Y with known σ_X and σ_Y. μ0 = hypothesised μ_X − μ_Y."),
    "Paired t-test": TestMeta(True, True, False, False,
                              "Uses rows where both X and Y exist. μ0 = hypothesised mean of X − Y."),
    "F-test (equality of variances)": TestMeta(True, False, False, False, "H0: σ²_X = σ²_Y."),
    "Wilcoxon signed-rank (one-sample)": TestMeta(False, True, False, False, "H0: median of X = μ0."),
    "Wilcoxon signed-rank (paired)": TestMeta(True, True, False, False, "H0: median of (X − Y) = μ0."),
    "Mann-Whitney U (two independent samples)": TestMeta(True, False, False, False,
                                                         "Non-parametric X vs Y."),
    "One-way ANOVA (all columns)": TestMeta(False, False, False, False,
                                            "Each numeric column is a group (alternative is ignored)."),
    "Kruskal-Wallis (all columns)": TestMeta(False, False, False, False,
                                             "Non-parametric ANOVA over all columns."),
    "Runs test (randomness about the median)": TestMeta(False, False, False, False,
                                                        "Are the values of X in random order? (trend / clustering check)"),
    "Sign test (median)": TestMeta(False, True, False, False, "H0: median of X = μ0 (very few assumptions)."),
    "Kolmogorov-Smirnov (two samples)": TestMeta(True, False, False, False,
                                                 "Do X and Y come from the same distribution?"),
    "Levene / Brown-Forsythe (all columns)": TestMeta(False, False, False, False,
                                                      "Equality of variances across all columns (robust)."),
    "Bartlett (all columns)": TestMeta(False, False, False, False,
                                       "Equality of variances across all columns (assumes normality)."),
    "Tukey HSD post-hoc (all columns)": TestMeta(False, False, False, False,
                                                 "All pairwise mean comparisons after ANOVA (≥ 3 columns)."),
}

PLOT_KINDS = [
    "Histogram + KDE + normal fit",
    "Histogram + best fitted PDFs",
    "Box plot (X)",
    "Box plots (all columns)",
    "Q-Q plot (normal)",
    "ECDF + normal CDF",
    "Run sequence (x̄ ± k·s)",
    "Scatter + regression (X vs Y)",
    "Residuals vs fitted (X vs Y)",
    "Correlation heatmap",
    "Autocorrelation (ACF)",
    "Lag plot  x[t] vs x[t+1]",
    "P-P plot (normal)",
    "Means ± CI (all columns)",
    "Scatter matrix (all columns)",
    "Histogram grid (all columns)",
]
FREQ_METHODS = ["sturges", "auto", "fd", "scott", "doane", "rice", "sqrt", "stone",
                "number of bins", "class width", "discrete (unique values)"]


class StatLab(ExtraTabs, tk.Tk):
    def __init__(self, path: Optional[str] = None):
        super().__init__()
        self.title(f"{APP_NAME} - Engineering Statistics & Probability Workbench")
        self.geometry("1400x900")
        self.minsize(1240, 720)
        self.configure(bg=BG)
        fam = set(tkfont.families())
        self.mono_name = next((f for f in ("JetBrains Mono", "Cascadia Mono", "Consolas", "DejaVu Sans Mono",
                                           "Menlo", "Liberation Mono", "Courier New") if f in fam), "TkFixedFont")
        self.mono = tkfont.Font(family=self.mono_name, size=10)
        self.df: Optional[pd.DataFrame] = None
        self.df0: Optional[pd.DataFrame] = None
        self.calc_widgets: list = []
        self.ignored: List[str] = []
        self.source = "(no data)"
        self.fits = None
        self.fits_key = None
        self.fits_dirty = True
        self.v_x = tk.StringVar()
        self.v_y = tk.StringVar(value="(none)")
        self.v_alpha = tk.StringVar(value="0.05")
        self.v_sig = tk.StringVar(value="6")
        self.v_trim = tk.StringVar(value="10")
        self.v_qm = tk.StringVar(value="linear")
        self.v_header = tk.StringVar(value="auto")
        self.v_dec = tk.StringVar(value="auto")
        self.v_fm = tk.StringVar(value="sturges")
        self.v_fp = tk.StringVar(value="10")
        self.v_plot = tk.StringVar(value=PLOT_KINDS[0])
        self.v_test = tk.StringVar(value="One-sample t-test")
        self.v_alt = tk.StringVar(value="two-sided")
        self.v_mu0 = tk.StringVar(value="0")
        self.v_s1 = tk.StringVar(value="1")
        self.v_s2 = tk.StringVar(value="1")
        self.v_cm = tk.StringVar(value="pearson")
        self.v_x0 = tk.StringVar(value="")
        self.v_dist = tk.StringVar(value="Normal")
        self.v_px = tk.StringVar(value="1")
        self.v_pa = tk.StringVar(value="-1")
        self.v_pb = tk.StringVar(value="1")
        self.v_pp = tk.StringVar(value="0.95")
        self.pvars: List[tk.StringVar] = []
        self._all_cache = ([], [], {})
        self._style()
        self._build()
        self._bind_keys()
        self.set_status("Ready - open a data file (Ctrl+O) or paste numbers in the DATA tab.")
        self.build_params()
        if path:
            self.after(150, lambda: self.load_path(path))

    # ------------------------------------------------------------------ style
    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        base = (self.mono_name, 10)
        s.configure(".", background=BG, foreground=FG, fieldbackground=PANEL, bordercolor=BORDER,
                    lightcolor=BORDER, darkcolor=BORDER, troughcolor=PANEL, font=base,
                    focuscolor=ACCENT, selectbackground=SEL, selectforeground=ACCENT)
        s.configure("TFrame", background=BG)
        s.configure("Panel.TFrame", background=PANEL)
        s.configure("TLabel", background=BG, foreground=FG)
        s.configure("Dim.TLabel", foreground=DIM)
        s.configure("Accent.TLabel", foreground=ACCENT, font=(self.mono_name, 10, "bold"))
        s.configure("Warn.TLabel", foreground=WARN)
        s.configure("Status.TLabel", background=PANEL, foreground=DIM, padding=(10, 4))
        s.configure("TLabelframe", background=BG, bordercolor=BORDER)
        s.configure("TLabelframe.Label", background=BG, foreground=CYAN, font=(self.mono_name, 10, "bold"))
        s.configure("TButton", background=PANEL2, foreground=ACCENT, bordercolor=BORDER, padding=(10, 4))
        s.map("TButton", background=[("active", SEL), ("pressed", SEL)], foreground=[("disabled", DIM)])
        s.configure("Go.TButton", background=SEL, foreground=ACCENT, font=(self.mono_name, 10, "bold"))
        s.configure("TEntry", fieldbackground=PANEL, foreground=FG, insertcolor=ACCENT, bordercolor=BORDER)
        s.map("TEntry", fieldbackground=[("focus", PANEL2)], bordercolor=[("focus", ACCENT)])
        s.configure("TCombobox", fieldbackground=PANEL, background=PANEL2, foreground=FG,
                    arrowcolor=ACCENT, bordercolor=BORDER, insertcolor=ACCENT)
        s.map("TCombobox", fieldbackground=[("readonly", PANEL)], foreground=[("readonly", FG)],
              selectbackground=[("readonly", PANEL)], selectforeground=[("readonly", FG)],
              bordercolor=[("focus", ACCENT)])
        s.configure("TSpinbox", fieldbackground=PANEL, background=PANEL2, foreground=FG, arrowcolor=ACCENT,
                    bordercolor=BORDER, insertcolor=ACCENT)
        s.configure("TNotebook", background=BG, bordercolor=BORDER, tabmargins=(0, 4, 0, 0))
        s.configure("TNotebook.Tab", background=PANEL, foreground=DIM, padding=(6, 5), bordercolor=BORDER,
                    font=(self.mono_name, 8))
        s.configure("Inner.TNotebook", background=BG, bordercolor=BORDER, tabmargins=(0, 2, 0, 0))
        s.configure("Inner.TNotebook.Tab", background=PANEL, foreground=DIM, padding=(10, 4), bordercolor=BORDER,
                    font=(self.mono_name, 9))
        s.map("Inner.TNotebook.Tab", background=[("selected", PANEL2)], foreground=[("selected", CYAN)])
        s.map("TNotebook.Tab", background=[("selected", PANEL2)], foreground=[("selected", ACCENT)])
        s.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=FG, rowheight=22,
                    bordercolor=BORDER)
        s.map("Treeview", background=[("selected", SEL)], foreground=[("selected", ACCENT)])
        s.configure("Treeview.Heading", background=PANEL2, foreground=CYAN, relief="flat",
                    font=(self.mono_name, 10, "bold"))
        s.map("Treeview.Heading", background=[("active", SEL)])
        for o in ("Vertical", "Horizontal"):
            s.configure(f"{o}.TScrollbar", background=PANEL2, troughcolor=PANEL, arrowcolor=ACCENT,
                        bordercolor=BORDER)
        s.configure("TCheckbutton", background=BG, foreground=FG)
        s.configure("TPanedwindow", background=BG)
        s.configure("Sash", background=BORDER)
        self.option_add("*TCombobox*Listbox.background", PANEL)
        self.option_add("*TCombobox*Listbox.foreground", FG)
        self.option_add("*TCombobox*Listbox.selectBackground", SEL)
        self.option_add("*TCombobox*Listbox.selectForeground", ACCENT)
        self.option_add("*TCombobox*Listbox.font", self.mono)

    # ---------------------------------------------------------------- widgets
    def mk_text(self, parent, height=10):
        fr = ttk.Frame(parent)
        t = tk.Text(fr, bg=PANEL, fg=FG, insertbackground=ACCENT, font=self.mono, relief="flat",
                    wrap="none", padx=10, pady=8, height=height, highlightthickness=1,
                    highlightbackground=BORDER, highlightcolor=BORDER, selectbackground=SEL,
                    selectforeground=ACCENT, state="disabled", undo=False)
        sy = ttk.Scrollbar(fr, orient="vertical", command=t.yview)
        sx = ttk.Scrollbar(fr, orient="horizontal", command=t.xview)
        t.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        t.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")
        fr.rowconfigure(0, weight=1)
        fr.columnconfigure(0, weight=1)
        t.tag_configure("head", foreground=ACCENT, font=(self.mono_name, 10, "bold"))
        t.tag_configure("ok", foreground=CYAN)
        t.tag_configure("bad", foreground=WARN, font=(self.mono_name, 10, "bold"))
        t.tag_configure("dim", foreground=DIM)
        t.tag_configure("err", foreground=ERR)
        return fr, t

    def set_text(self, t: tk.Text, s: str):
        t.config(state="normal")
        t.delete("1.0", "end")
        t.insert("end", s)
        src = s.split("\n")
        for i, line in enumerate(src, start=1):
            tag = None
            st = line.strip()
            nxt = src[i].strip() if i < len(src) else ""
            if st.startswith("ERROR"):
                tag = "err"
            elif "FAIL TO REJECT" in line or "Do not reject" in line:
                tag = "ok"
            elif "REJECT H0" in line or "Reject normality" in line or "WARNING" in line:
                tag = "bad"
            elif st and set(st) <= set("=-"):
                tag = "dim"
            elif st and len(nxt) >= 6 and set(nxt) == {"="}:
                tag = "head"
            elif re.match(r"^(TEST:|SIMPLE LINEAR|EMPIRICAL|CORRELATION|P-VALUES|COVARIANCE|PAIR|STEM-AND|"
                          r"NORMALITY|OUTLIER|PREDICTION)", st):
                tag = "head"
            if tag:
                t.tag_add(tag, f"{i}.0", f"{i}.end")
        t.config(state="disabled")

    def mk_tree(self, parent, cols, widths=None, anchors=None, height=12):
        fr = ttk.Frame(parent)
        tree = ttk.Treeview(fr, columns=cols, show="headings", height=height, selectmode="extended")
        sy = ttk.Scrollbar(fr, orient="vertical", command=tree.yview)
        sx = ttk.Scrollbar(fr, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        tree.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")
        fr.rowconfigure(0, weight=1)
        fr.columnconfigure(0, weight=1)
        tree.tag_configure("group", foreground=ACCENT, background=PANEL2)
        tree.tag_configure("bad", foreground=WARN)
        tree.tag_configure("ok", foreground=CYAN)
        self.set_cols(tree, cols, widths, anchors)
        self.bind_tree_copy(tree)
        return fr, tree

    def set_cols(self, tree, cols, widths=None, anchors=None):
        tree["columns"] = list(cols)
        for i, c in enumerate(cols):
            tree.heading(c, text=c)
            w = widths[i] if widths else 110
            a = anchors[i] if anchors else "w"
            tree.column(c, width=w, minwidth=50, anchor=a, stretch=(i == len(cols) - 1 or not widths))

    def bind_tree_copy(self, tree):
        def copy(_e=None):
            sel = tree.selection() or tree.get_children()
            head = "\t".join(str(tree.heading(c)["text"]) for c in tree["columns"])
            lines = [head] + ["\t".join(str(v) for v in tree.item(i, "values")) for i in sel]
            self.clipboard_clear()
            self.clipboard_append("\n".join(lines))
            self.set_status(f"Copied {len(lines) - 1} row(s) to clipboard.")
            return "break"

        tree.bind("<Control-c>", copy)
        tree.bind("<Control-a>", lambda e: (tree.selection_set(tree.get_children()), "break")[1])
        menu = tk.Menu(tree, tearoff=0, bg=PANEL2, fg=FG, activebackground=SEL, activeforeground=ACCENT, bd=0)
        menu.add_command(label="Copy selected rows (or all)", command=copy)
        for b in ("<Button-3>", "<Button-2>"):
            tree.bind(b, lambda e: menu.tk_popup(e.x_root, e.y_root))

    def mk_figure(self, parent):
        holder = ttk.Frame(parent)
        fig = Figure(figsize=(6, 4), dpi=100, facecolor=BG)
        try:
            fig.set_layout_engine("tight")
        except Exception:
            pass
        canvas = FigureCanvasTkAgg(fig, master=holder)
        try:
            tb = NavigationToolbar2Tk(canvas, holder, pack_toolbar=False)
            tb.config(background=PANEL)
            for w in tb.winfo_children():
                try:
                    w.config(background=PANEL, highlightbackground=PANEL, bd=0)
                    w.config(foreground=FG)
                except tk.TclError:
                    pass
                if isinstance(w, (tk.Button, tk.Checkbutton)) and hasattr(tb, "_set_image_for_button"):
                    try:
                        tb._set_image_for_button(w)
                    except Exception:
                        pass
            tb.pack(side="bottom", fill="x")
        except Exception:
            pass
        canvas.get_tk_widget().configure(bg=BG, highlightthickness=0)
        canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

        def sync(_e=None):
            """Re-fit the figure to the widget (fixes clipping when Tk DPI scaling != 1)."""
            try:
                w = canvas.get_tk_widget()
                if w.winfo_width() > 10 and w.winfo_height() > 10:
                    ev = type("Ev", (), {"width": w.winfo_width(), "height": w.winfo_height()})()
                    canvas.resize(ev)
                    canvas.draw_idle()
            except Exception:
                pass

        canvas.get_tk_widget().bind("<Map>", lambda e: self.after_idle(sync), add="+")
        return fig, canvas, holder

    def row(self, parent, *items, pady=3):
        """Pack a horizontal row of (label|widget) items."""
        fr = ttk.Frame(parent)
        for it in items:
            if isinstance(it, str):
                ttk.Label(fr, text=it, style="Dim.TLabel").pack(side="left", padx=(8, 4))
            else:
                it.pack(side="left", padx=2)
        fr.pack(fill="x", pady=pady)
        return fr

    # ------------------------------------------------------------------ build
    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=(10, 4))
        ttk.Label(top, text="◢ STAT LAB", style="Accent.TLabel").pack(side="left", padx=(0, 14))
        for txt, cmd in (("Open file", self.open_file), ("Export report", self.export_report),
                         ("Refresh F5", self.refresh)):
            ttk.Button(top, text=txt, command=cmd).pack(side="left", padx=2)
        ttk.Label(top, text="   X", style="Dim.TLabel").pack(side="left")
        self.cb_x = ttk.Combobox(top, textvariable=self.v_x, state="readonly", width=16)
        self.cb_x.pack(side="left", padx=3)
        ttk.Label(top, text="Y", style="Dim.TLabel").pack(side="left")
        self.cb_y = ttk.Combobox(top, textvariable=self.v_y, state="readonly", width=16, values=["(none)"])
        self.cb_y.pack(side="left", padx=3)
        ttk.Label(top, text="  α", style="Dim.TLabel").pack(side="left")
        e = ttk.Entry(top, textvariable=self.v_alpha, width=6)
        e.pack(side="left", padx=3)
        e.bind("<Return>", self.refresh)
        ttk.Label(top, text="trim %", style="Dim.TLabel").pack(side="left")
        e = ttk.Entry(top, textvariable=self.v_trim, width=4)
        e.pack(side="left", padx=3)
        e.bind("<Return>", self.refresh)
        ttk.Label(top, text="quantile", style="Dim.TLabel").pack(side="left")
        cb = ttk.Combobox(top, textvariable=self.v_qm, values=QUANTILE_METHODS, state="readonly", width=14)
        cb.pack(side="left", padx=3)
        cb.bind("<<ComboboxSelected>>", self.refresh)
        ttk.Label(top, text="digits", style="Dim.TLabel").pack(side="left")
        sp = ttk.Spinbox(top, from_=3, to=15, textvariable=self.v_sig, width=3, command=self.refresh)
        sp.pack(side="left", padx=3)
        sp.bind("<Return>", self.refresh)
        self.cb_x.bind("<<ComboboxSelected>>", self.on_var_change)
        self.cb_y.bind("<<ComboboxSelected>>", self.on_var_change)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10, pady=4)
        self.tabs = {}
        for key, title in (("data", "DATA"), ("transform", "TRANSFORM"), ("desc", "DESCRIPTIVE"),
                           ("freq", "FREQUENCY"), ("plots", "PLOTS"), ("diag", "DIAGNOSTICS"),
                           ("fit", "DIST. FIT"), ("tests", "TESTS"), ("rel", "CORR & REGR"),
                           ("prob", "PROB. CALC"), ("spc", "SPC & RELIAB."), ("adv", "ADVANCED"),
                           ("calc", "CALCULATORS"), ("all", "ALL COLS")):
            f = ttk.Frame(self.nb)
            self.nb.add(f, text=f" {title} ")
            self.tabs[key] = f
        self._tab_data()
        self._tab_transform()
        self._tab_desc()
        self._tab_freq()
        self._tab_plots()
        self._tab_diag()
        self._tab_fit()
        self._tab_tests()
        self._tab_rel()
        self._tab_prob()
        self._tab_spc()
        self._tab_adv()
        self._tab_calc()
        self._tab_all()
        self.status = ttk.Label(self, text="", style="Status.TLabel", anchor="w")
        self.status.pack(fill="x", side="bottom")

    def _bind_keys(self):
        self.bind("<F5>", self.refresh)
        self.bind("<Control-o>", lambda e: self.open_file())
        self.bind("<Control-s>", lambda e: self.export_report())
        self.nb.bind("<<NotebookTabChanged>>", self.on_tab)

    def set_status(self, msg: str, err: bool = False):
        self.status.configure(text=msg, foreground=ERR if err else DIM)

    # ---- DATA tab
    def _tab_data(self):
        f = self.tabs["data"]
        pw = ttk.PanedWindow(f, orient="horizontal")
        pw.pack(fill="both", expand=True, padx=6, pady=6)
        left = ttk.Frame(pw, width=420)
        right = ttk.Frame(pw)
        pw.add(left, weight=0)
        pw.add(right, weight=1)
        lf = ttk.LabelFrame(left, text=" FILE INPUT ")
        lf.pack(fill="x", padx=4, pady=4)
        ttk.Button(lf, text="Open file…  (Ctrl+O)", style="Go.TButton", command=self.open_file).pack(
            fill="x", padx=8, pady=(8, 4))
        ttk.Label(lf, text="CSV · TSV · TXT · DAT · XLSX · XLS · JSON", style="Dim.TLabel").pack(padx=8)
        r = ttk.Frame(lf)
        r.pack(fill="x", padx=8, pady=6)
        ttk.Label(r, text="Header row", style="Dim.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Combobox(r, textvariable=self.v_header, values=["auto", "yes", "no"], state="readonly",
                     width=8).grid(row=0, column=1, padx=6, pady=2)
        ttk.Label(r, text="Decimal", style="Dim.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Combobox(r, textvariable=self.v_dec, values=["auto", ".", ","], state="readonly",
                     width=8).grid(row=1, column=1, padx=6, pady=2)
        ttk.Label(lf, text="Delimiter is detected automatically (; tab , | space).\n"
                           "Non-numeric columns are ignored; blanks = missing.", style="Dim.TLabel",
                  justify="left").pack(padx=8, pady=(0, 8), anchor="w")
        pf = ttk.LabelFrame(left, text=" MANUAL / PASTE INPUT ")
        pf.pack(fill="both", expand=True, padx=4, pady=4)
        fr, self.t_paste = self.mk_text(pf, height=10)
        self.t_paste.config(state="normal")
        self.t_paste.insert("end", "# paste numbers here (one per line, or a table with a header)\n"
                                   "12.1\n11.8\n12.4\n12.0\n11.9\n12.3\n")
        fr.pack(fill="both", expand=True, padx=8, pady=8)
        ttk.Button(pf, text="Use this data", style="Go.TButton", command=self.use_pasted).pack(
            fill="x", padx=8, pady=(0, 8))
        ttk.Label(right, text="PREVIEW", style="Accent.TLabel").pack(anchor="w", padx=6)
        fr, self.tr_prev = self.mk_tree(right, ["#"], [60], height=18)
        fr.pack(fill="both", expand=True, padx=4, pady=4)
        self.lbl_info = ttk.Label(right, text="No data loaded.", style="Dim.TLabel", justify="left")
        self.lbl_info.pack(anchor="w", padx=6, pady=4)

    # ---- DESCRIPTIVE tab
    def _tab_desc(self):
        f = self.tabs["desc"]
        self.lbl_desc = ttk.Label(f, text="", style="Accent.TLabel")
        self.lbl_desc.pack(anchor="w", padx=8, pady=(8, 2))
        fr, self.tr_desc = self.mk_tree(f, ["Statistic", "Value", "Note"], [380, 260, 420])
        fr.pack(fill="both", expand=True, padx=6, pady=4)
        ttk.Label(f, text="Ctrl+C or right-click copies the selected rows. Change α / trim / quantile "
                          "method / digits in the top bar (press Enter).", style="Dim.TLabel").pack(
            anchor="w", padx=8, pady=(0, 6))

    # ---- FREQUENCY tab
    def _tab_freq(self):
        f = self.tabs["freq"]
        bar = ttk.Frame(f)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Label(bar, text="Class rule", style="Dim.TLabel").pack(side="left", padx=(4, 4))
        cb = ttk.Combobox(bar, textvariable=self.v_fm, values=FREQ_METHODS, state="readonly", width=24)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", self.refresh)
        ttk.Label(bar, text="bins / width", style="Dim.TLabel").pack(side="left", padx=(12, 4))
        e = ttk.Entry(bar, textvariable=self.v_fp, width=8)
        e.pack(side="left")
        e.bind("<Return>", self.refresh)
        ttk.Button(bar, text="Update", command=self.refresh).pack(side="left", padx=8)
        self.lbl_freq = ttk.Label(bar, text="", style="Dim.TLabel")
        self.lbl_freq.pack(side="left", padx=8)
        pw = ttk.PanedWindow(f, orient="horizontal")
        pw.pack(fill="both", expand=True, padx=6, pady=4)
        fr, self.tr_freq = self.mk_tree(pw, ["Class"], [150])
        pw.add(fr, weight=3)
        fr2, self.t_stem = self.mk_text(pw)
        pw.add(fr2, weight=2)

    # ---- PLOTS tab
    def _tab_plots(self):
        f = self.tabs["plots"]
        bar = ttk.Frame(f)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Label(bar, text="Plot", style="Dim.TLabel").pack(side="left", padx=(4, 4))
        cb = ttk.Combobox(bar, textvariable=self.v_plot, values=PLOT_KINDS, state="readonly", width=34)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self.draw_plot())
        ttk.Button(bar, text="Draw", style="Go.TButton", command=self.draw_plot).pack(side="left", padx=8)
        ttk.Button(bar, text="Save image…", command=lambda: self.save_fig(self.fig_main)).pack(side="left")
        ttk.Label(bar, text="class rule is taken from the FREQUENCY tab", style="Dim.TLabel").pack(
            side="left", padx=12)
        self.fig_main, self.canvas_main, holder = self.mk_figure(f)
        holder.pack(fill="both", expand=True, padx=6, pady=4)

    # ---- DIAGNOSTICS tab
    def _tab_diag(self):
        f = self.tabs["diag"]
        pw = ttk.PanedWindow(f, orient="vertical")
        pw.pack(fill="both", expand=True, padx=6, pady=6)
        top = ttk.Frame(pw)
        ttk.Label(top, text="NORMALITY TESTS   (H0: the data come from a normal distribution)",
                  style="Accent.TLabel").pack(anchor="w", padx=4, pady=(0, 3))
        fr, self.tr_norm = self.mk_tree(top, ["Test", "Statistic", "p-value", "Decision", "Note"],
                                        [230, 320, 100, 150, 400], height=7)
        fr.pack(fill="both", expand=True)
        pw.add(top, weight=1)
        bot = ttk.Frame(pw)
        ttk.Label(bot, text="OUTLIER DETECTION", style="Accent.TLabel").pack(anchor="w", padx=4, pady=(6, 3))
        fr2, self.t_out = self.mk_text(bot)
        fr2.pack(fill="both", expand=True)
        pw.add(bot, weight=2)

    # ---- FIT tab
    def _tab_fit(self):
        f = self.tabs["fit"]
        bar = ttk.Frame(f)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Button(bar, text="Run fit", style="Go.TButton", command=lambda: self.upd_fit(force=True)).pack(
            side="left", padx=4)
        ttk.Label(bar, text="Maximum-likelihood fits ranked by AIC (lowest = best). Positive-support "
                            "families use location = 0.", style="Dim.TLabel").pack(side="left", padx=8)
        cols = ["Rank", "Distribution", "Parameters", "logL", "AIC", "ΔAIC", "BIC", "KS D", "KS p"]
        fr, self.tr_fit = self.mk_tree(f, cols, [50, 140, 330, 100, 100, 80, 100, 80, 80],
                                       ["center", "w", "w", "e", "e", "e", "e", "e", "e"])
        fr.pack(fill="both", expand=True, padx=6, pady=4)
        ttk.Label(f, text="KS p-values are optimistic (parameters are estimated from the same data) - rank "
                          "by AIC/BIC and inspect the 'Histogram + best fitted PDFs' and Q-Q plots.",
                  style="Dim.TLabel").pack(anchor="w", padx=8, pady=(0, 6))

    # ---- TESTS tab
    def _tab_tests(self):
        f = self.tabs["tests"]
        pw = ttk.PanedWindow(f, orient="horizontal")
        pw.pack(fill="both", expand=True, padx=6, pady=6)
        left = ttk.Frame(pw, width=400)
        pw.add(left, weight=0)
        lf = ttk.LabelFrame(left, text=" TEST SETUP ")
        lf.pack(fill="x", padx=4, pady=4)
        g = ttk.Frame(lf)
        g.pack(fill="x", padx=8, pady=8)
        ttk.Label(g, text="Test", style="Dim.TLabel").grid(row=0, column=0, sticky="w", pady=3)
        self.cb_test = ttk.Combobox(g, textvariable=self.v_test, values=list(TEST_META), state="readonly",
                                    width=38)
        self.cb_test.grid(row=1, column=0, columnspan=2, sticky="we", pady=3)
        self.cb_test.bind("<<ComboboxSelected>>", self.on_test_change)
        ttk.Label(g, text="Alternative H1", style="Dim.TLabel").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Combobox(g, textvariable=self.v_alt, values=["two-sided", "less", "greater"], state="readonly",
                     width=12).grid(row=2, column=1, sticky="w", pady=3)
        self.lbl_mu0 = ttk.Label(g, text="μ0  (hypothesised)", style="Dim.TLabel")
        self.lbl_mu0.grid(row=3, column=0, sticky="w", pady=3)
        self.e_mu0 = ttk.Entry(g, textvariable=self.v_mu0, width=14)
        self.e_mu0.grid(row=3, column=1, sticky="w", pady=3)
        self.lbl_s1 = ttk.Label(g, text="σ  (known / σ0)", style="Dim.TLabel")
        self.lbl_s1.grid(row=4, column=0, sticky="w", pady=3)
        self.e_s1 = ttk.Entry(g, textvariable=self.v_s1, width=14)
        self.e_s1.grid(row=4, column=1, sticky="w", pady=3)
        self.lbl_s2 = ttk.Label(g, text="σ_Y  (known)", style="Dim.TLabel")
        self.lbl_s2.grid(row=5, column=0, sticky="w", pady=3)
        self.e_s2 = ttk.Entry(g, textvariable=self.v_s2, width=14)
        self.e_s2.grid(row=5, column=1, sticky="w", pady=3)
        self.lbl_hint = ttk.Label(lf, text="", style="Dim.TLabel", wraplength=360, justify="left")
        self.lbl_hint.pack(fill="x", padx=8, pady=(0, 6))
        ttk.Button(lf, text="Run test", style="Go.TButton", command=self.run_selected_test).pack(
            fill="x", padx=8, pady=(0, 10))
        ttk.Label(left, text="Significance level α is set in the top bar.\nSamples X / Y are chosen in "
                             "the top bar as well.", style="Dim.TLabel", justify="left").pack(
            anchor="w", padx=8, pady=4)
        fr, self.t_test = self.mk_text(pw)
        pw.add(fr, weight=1)
        self.on_test_change()

    # ---- RELATIONS tab
    def _tab_rel(self):
        f = self.tabs["rel"]
        bar = ttk.Frame(f)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Label(bar, text="Correlation", style="Dim.TLabel").pack(side="left", padx=(4, 4))
        ttk.Combobox(bar, textvariable=self.v_cm, values=["pearson", "spearman", "kendall"],
                     state="readonly", width=10).pack(side="left")
        ttk.Label(bar, text="predict at x0", style="Dim.TLabel").pack(side="left", padx=(14, 4))
        ttk.Entry(bar, textvariable=self.v_x0, width=10).pack(side="left")
        ttk.Button(bar, text="Run analysis", style="Go.TButton", command=self.run_relations).pack(
            side="left", padx=10)
        ttk.Label(bar, text="matrices use all columns (pairwise complete); regression uses Y = f(X) from "
                            "the top bar", style="Dim.TLabel").pack(side="left", padx=6)
        fr, self.t_rel = self.mk_text(f)
        fr.pack(fill="both", expand=True, padx=6, pady=4)

    # ---- PROBABILITY tab
    def _tab_prob(self):
        f = self.tabs["prob"]
        pw = ttk.PanedWindow(f, orient="horizontal")
        pw.pack(fill="both", expand=True, padx=6, pady=6)
        left = ttk.Frame(pw, width=330)
        pw.add(left, weight=0)
        lf = ttk.LabelFrame(left, text=" DISTRIBUTION ")
        lf.pack(fill="x", padx=4, pady=4)
        cb = ttk.Combobox(lf, textvariable=self.v_dist, values=[d.name for d in DISTRIBUTIONS],
                          state="readonly", width=30)
        cb.pack(padx=8, pady=(8, 4), anchor="w")
        cb.bind("<<ComboboxSelected>>", self.build_params)
        self.lbl_note = ttk.Label(lf, text="", style="Dim.TLabel")
        self.lbl_note.pack(anchor="w", padx=8)
        self.param_frame = ttk.Frame(lf)
        self.param_frame.pack(fill="x", padx=8, pady=8)
        ttk.Button(lf, text="Estimate parameters from X", command=self.use_estimates).pack(
            fill="x", padx=8, pady=(0, 8))
        qf = ttk.LabelFrame(left, text=" QUERY ")
        qf.pack(fill="x", padx=4, pady=4)
        g = ttk.Frame(qf)
        g.pack(fill="x", padx=8, pady=8)
        for r_, (lab, var) in enumerate((("x   (point)", self.v_px), ("a   (lower)", self.v_pa),
                                         ("b   (upper)", self.v_pb), ("p   (probability)", self.v_pp))):
            ttk.Label(g, text=lab, style="Dim.TLabel").grid(row=r_, column=0, sticky="w", pady=3)
            e = ttk.Entry(g, textvariable=var, width=14)
            e.grid(row=r_, column=1, padx=8, pady=3)
            e.bind("<Return>", lambda ev: self.compute_prob())
        ttk.Label(qf, text="Leave a field empty to skip it.\nx → pdf/pmf, CDF, tails · a,b → interval\n"
                           "p → quantile (inverse CDF)", style="Dim.TLabel", justify="left").pack(
            anchor="w", padx=8, pady=(0, 6))
        ttk.Button(qf, text="Compute", style="Go.TButton", command=self.compute_prob).pack(
            fill="x", padx=8, pady=(0, 8))
        right = ttk.PanedWindow(pw, orient="vertical")
        pw.add(right, weight=1)
        self.fig_prob, self.canvas_prob, holder = self.mk_figure(right)
        right.add(holder, weight=3)
        fr, self.t_prob = self.mk_text(right, height=10)
        right.add(fr, weight=2)

    # ---- ALL COLUMNS tab
    def _tab_all(self):
        f = self.tabs["all"]
        bar = ttk.Frame(f)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Button(bar, text="Export table (CSV / XLSX)…", command=self.export_all).pack(side="left", padx=4)
        ttk.Label(bar, text="Descriptive statistics of every numeric column side by side.",
                  style="Dim.TLabel").pack(side="left", padx=8)
        fr, self.tr_all = self.mk_tree(f, ["Statistic"], [320])
        fr.pack(fill="both", expand=True, padx=6, pady=4)

    # ------------------------------------------------------------ parameters
    def fnum(self, s: str, label: str) -> float:
        try:
            v = float(str(s).strip().replace(",", "."))
        except ValueError:
            raise ValueError(f"{label} must be a number (got '{s}').")
        if not math.isfinite(v):
            raise ValueError(f"{label} must be finite.")
        return v

    def alpha(self) -> float:
        a = self.fnum(self.v_alpha.get(), "α")
        if not 0 < a < 1:
            raise ValueError("α must be strictly between 0 and 1.")
        return a

    def trim(self) -> float:
        t = self.fnum(self.v_trim.get(), "trim %") / 100
        if not 0 <= t < 0.5:
            raise ValueError("trim % must be in [0, 50).")
        return t

    def get_x(self):
        if self.df is None or self.v_x.get() not in self.df.columns:
            raise ValueError("No data loaded - open a file or paste numbers first.")
        s = self.df[self.v_x.get()]
        m = s.notna().to_numpy()
        return s.to_numpy(float)[m], np.flatnonzero(m) + 1, int((~m).sum())

    def get_xy(self):
        cx, cy = self.v_x.get(), self.v_y.get()
        if cy in ("", "(none)") or cy not in self.df.columns:
            raise ValueError("Choose a Y variable in the top bar (needs at least two numeric columns).")
        return pair_clean(self.df, cx, cy)

    # --------------------------------------------------------------- loading
    def open_file(self):
        p = filedialog.askopenfilename(
            title="Open data file",
            filetypes=[("Data files", "*.csv *.tsv *.txt *.dat *.xlsx *.xlsm *.xls *.ods *.json"),
                       ("All files", "*.*")])
        if p:
            self.load_path(p)

    def ask_choice(self, title, prompt, options):
        win = tk.Toplevel(self)
        win.title(title)
        win.configure(bg=BG)
        win.transient(self)
        ttk.Label(win, text=prompt).pack(padx=16, pady=(16, 6))
        var = tk.StringVar(value=options[0])
        ttk.Combobox(win, values=options, textvariable=var, state="readonly", width=34).pack(padx=16, pady=6)
        res = {"v": None}

        def ok(_e=None):
            res["v"] = var.get()
            win.destroy()

        ttk.Button(win, text="OK", style="Go.TButton", command=ok).pack(pady=(6, 16))
        win.bind("<Return>", ok)
        win.update_idletasks()
        win.geometry(f"+{self.winfo_rootx() + 300}+{self.winfo_rooty() + 200}")
        win.grab_set()
        self.wait_window(win)
        return res["v"]

    def load_path(self, path: str):
        try:
            sheet = None
            if os.path.splitext(path)[1].lower() in (".xlsx", ".xlsm", ".xls", ".ods"):
                sheets = excel_sheets(path)
                if len(sheets) > 1:
                    sheet = self.ask_choice("Select sheet", "This workbook has several sheets:", sheets)
                    if sheet is None:
                        return
            df, ign = load_file(path, self.v_header.get(), self.v_dec.get(), sheet)
        except Exception as e:
            messagebox.showerror("Cannot load file", str(e))
            self.set_status(f"Load failed: {e}", err=True)
            return
        name = os.path.basename(path) + (f" [{sheet}]" if sheet else "")
        self.set_data(df, ign, name)

    def use_pasted(self):
        text = self.t_paste.get("1.0", "end")
        try:
            df, ign = frame_from_text(text, self.v_header.get(), self.v_dec.get())
        except Exception as e:
            messagebox.showerror("Cannot parse input", str(e))
            return
        self.set_data(df, ign, "(pasted data)")

    def set_data(self, df: pd.DataFrame, ignored: List[str], source: str):
        self.df, self.ignored, self.source = df.reset_index(drop=True), ignored, source
        self.df0, self.undo = self.df.copy(), []
        cols = list(self.df.columns)
        self.cb_x.configure(values=cols)
        self.cb_y.configure(values=["(none)"] + cols)
        self.v_x.set(cols[0])
        self.v_y.set(cols[1] if len(cols) > 1 else "(none)")
        self.fits, self.fits_dirty = None, True
        self.fill_preview()
        self.refresh()
        self.run_relations(silent=True)
        self.on_new_data()
        self.nb.select(self.tabs["desc"])

    def fill_preview(self):
        df = self.df
        cols = ["#"] + list(df.columns)
        self.set_cols(self.tr_prev, cols, [60] + [110] * len(df.columns),
                      ["e"] + ["e"] * len(df.columns))
        self.tr_prev.delete(*self.tr_prev.get_children())
        for i, rw in enumerate(df.head(500).itertuples(index=False), start=1):
            self.tr_prev.insert("", "end", values=[i] + ["" if (isinstance(v, float) and math.isnan(v))
                                                       else fmt(v, 10) for v in rw])
        miss = int(df.isna().sum().sum())
        msg = (f"Source: {self.source}\nRows: {len(df)}   numeric columns: {len(df.columns)}   "
               f"missing cells: {miss}")
        if self.ignored:
            msg += f"\nIgnored (non-numeric): {', '.join(map(str, self.ignored))}"
        if len(df) > 500:
            msg += "\nPreview shows the first 500 rows (all rows are analysed)."
        self.lbl_info.configure(text=msg)

    # ------------------------------------------------------------- refreshing
    def on_var_change(self, *_):
        self.fits, self.fits_dirty = None, True
        self.refresh()

    def on_tab(self, _e=None):
        if self.nb.select() == str(self.tabs["fit"]) and self.fits_dirty and self.df is not None:
            self.upd_fit()

    def refresh(self, *_):
        global SIG_DIGITS
        try:
            SIG_DIGITS = max(3, min(15, int(float(self.v_sig.get()))))
        except ValueError:
            pass
        if self.df is None:
            self.set_status("No data loaded.")
            return
        try:
            self.alpha()
            self.trim()
            self.upd_desc()
            self.upd_freq()
            self.upd_diag()
            self.upd_all()
            self.draw_plot()
            if self.nb.select() == str(self.tabs["fit"]):
                self.upd_fit()
            x, _, nm = self.get_x()
            self.set_status(f"{self.source}  |  X = {self.v_x.get()}  |  n = {len(x)}  |  "
                            f"missing = {nm}  |  α = {self.v_alpha.get()}")
        except ValueError as e:
            self.set_status(str(e), err=True)
            messagebox.showerror("Input error", str(e))
        except Exception as e:  # pragma: no cover
            traceback.print_exc()
            self.set_status(f"Error: {e}", err=True)

    def upd_desc(self):
        x, _, nm = self.get_x()
        self.lbl_desc.configure(text=f"VARIABLE: {self.v_x.get()}     n = {len(x)}     "
                                     f"confidence level = {(1 - self.alpha()) * 100:g}%")
        rows = describe(x, nm, 1 - self.alpha(), self.trim(), self.v_qm.get())
        t = self.tr_desc
        t.delete(*t.get_children())
        last = None
        for g, name, val, note in rows:
            if g != last:
                t.insert("", "end", values=(f"▌ {g}", "", ""), tags=("group",))
                last = g
            t.insert("", "end", values=("   " + name, fmt(val), note))

    def upd_freq(self):
        x, _, _ = self.get_x()
        try:
            p = float(self.v_fp.get().replace(",", "."))
        except ValueError:
            p = None
        cols, rows, info = frequency_table(x, self.v_fm.get(), p)
        n = len(cols)
        self.set_cols(self.tr_freq, cols, [170] + [105] * (n - 1), ["w"] + ["e"] * (n - 1))
        self.tr_freq.delete(*self.tr_freq.get_children())
        for r in rows:
            self.tr_freq.insert("", "end", values=[fmt(v) if not isinstance(v, str) else v for v in r])
        self.lbl_freq.configure(text=info)
        self.set_text(self.t_stem, stem_and_leaf(x))

    def upd_diag(self):
        x, rows, _ = self.get_x()
        a = self.alpha()
        t = self.tr_norm
        t.delete(*t.get_children())
        if len(x) < 3:
            self.set_text(self.t_out, "ERROR: need at least 3 observations.")
            return
        for name, stat, p, dec, note in normality_tests(x, a):
            t.insert("", "end", values=(name, stat, fmt_p(p), dec, note),
                     tags=("bad",) if dec.startswith("Reject") else ("ok",))
        rep = outlier_report(x, rows, a, self.v_qm.get())
        L = ["OUTLIER DETECTION  (row numbers refer to the data rows, starting at 1)", ""]
        if not rep:
            L.append("Not enough data.")
        for k, (desc, pts) in rep.items():
            L.append(f"{k}")
            L.append(f"   {desc}")
            if pts:
                L.append(f"   {len(pts)} flagged:  " + ",  ".join(f"row {int(r)} → {fmt(v)}" for r, v in pts[:40])
                         + (" ..." if len(pts) > 40 else ""))
            else:
                L.append("   none flagged")
            L.append("")
        L.append("Note: flagged points are candidates for investigation, not automatic deletions.")
        self.set_text(self.t_out, "\n".join(L))

    def upd_all(self):
        if self.df is None:
            return
        cols = list(self.df.columns)
        per, order = {}, []
        for c in cols:
            s = self.df[c]
            m = s.notna().to_numpy()
            r = describe(s.to_numpy(float)[m], int((~m).sum()), 1 - self.alpha(), self.trim(), self.v_qm.get())
            per[c] = {}
            for g, name, val, _ in r:
                per[c][(g, name)] = val
                if (g, name) not in order:
                    order.append((g, name))
        t = self.tr_all
        self.set_cols(t, ["Statistic"] + cols, [330] + [130] * len(cols), ["w"] + ["e"] * len(cols))
        t.delete(*t.get_children())
        last = None
        for g, name in order:
            if g != last:
                t.insert("", "end", values=[f"▌ {g}"] + [""] * len(cols), tags=("group",))
                last = g
            t.insert("", "end", values=["   " + name] + [fmt(per[c].get((g, name), "")) if (g, name) in per[c]
                                                          else "" for c in cols])
        self._all_cache = (cols, order, per)

    def upd_fit(self, force: bool = False):
        if self.df is None:
            return
        key = (self.v_x.get(), id(self.df))
        if force or self.fits is None or self.fits_key != key:
            x, _, _ = self.get_x()
            self.config(cursor="watch")
            self.update_idletasks()
            try:
                self.fits = fit_distributions(x)
                self.fits_key = key
            except ValueError as e:
                self.fits = []
                self.tr_fit.delete(*self.tr_fit.get_children())
                self.set_status(str(e), err=True)
                self.config(cursor="")
                return
            finally:
                self.config(cursor="")
        self.fits_dirty = False
        t = self.tr_fit
        t.delete(*t.get_children())
        for i, r in enumerate(self.fits, start=1):
            t.insert("", "end", values=(i, r["name"], r["pretty"], fmt(r["ll"]), fmt(r["aic"]),
                                        fmt(r["daic"]), fmt(r["bic"]), fmt(r["ks"]), fmt_p(r["ksp"])),
                     tags=("ok",) if i == 1 else ())

    # ------------------------------------------------------------------ plots
    def style_ax(self, ax, title=None, xl=None, yl=None):
        ax.set_facecolor(PANEL)
        for sp in ax.spines.values():
            sp.set_color(BORDER)
        ax.tick_params(colors=FG, labelsize=9)
        ax.grid(True, color=BORDER, linewidth=0.6, alpha=0.9)
        ax.set_axisbelow(True)
        if title:
            ax.set_title(title, color=ACCENT, fontsize=11, loc="left")
        if xl:
            ax.set_xlabel(xl, color=FG)
        if yl:
            ax.set_ylabel(yl, color=FG)

    def style_legend(self, ax):
        h, _ = ax.get_legend_handles_labels()
        if h:
            ax.legend(facecolor=PANEL2, edgecolor=BORDER, labelcolor=FG, fontsize=9)

    def hist_edges(self, x):
        try:
            p = float(self.v_fp.get().replace(",", "."))
        except ValueError:
            p = None
        return bin_edges(x, self.v_fm.get(), p)

    def draw_plot(self):
        if self.df is None:
            return
        fig = self.fig_main
        fig.clear()
        kind = self.v_plot.get()
        try:
            ax = fig.add_subplot(111)
            fn = {
                PLOT_KINDS[0]: self.p_hist, PLOT_KINDS[1]: self.p_hist_fit, PLOT_KINDS[2]: self.p_box,
                PLOT_KINDS[3]: self.p_box_all, PLOT_KINDS[4]: self.p_qq, PLOT_KINDS[5]: self.p_ecdf,
                PLOT_KINDS[6]: self.p_run, PLOT_KINDS[7]: self.p_scatter, PLOT_KINDS[8]: self.p_resid,
                PLOT_KINDS[9]: self.p_heat, PLOT_KINDS[10]: self.p_acf, PLOT_KINDS[11]: self.p_lag,
                PLOT_KINDS[12]: self.p_pp, PLOT_KINDS[13]: self.p_means, PLOT_KINDS[14]: self.p_matrix,
                PLOT_KINDS[15]: self.p_hgrid,
            }[kind]
            fn(ax)
        except Exception as e:
            fig.clear()
            ax = fig.add_subplot(111)
            self.style_ax(ax)
            ax.set_axis_off()
            ax.text(0.5, 0.5, f"{e}", ha="center", va="center", color=WARN, transform=ax.transAxes,
                    wrap=True, fontsize=11)
        try:
            fig.tight_layout()
        except Exception:
            pass
        self.canvas_main.draw_idle()

    def p_hist(self, ax):
        x, _, _ = self.get_x()
        n = len(x)
        edges = self.hist_edges(x)
        ax.hist(x, bins=edges, density=True, color=ACCENT, alpha=0.55, edgecolor=BG, label=f"data (n = {n})")
        if n > 1 and np.ptp(x) > 0:
            pad = 0.15 * np.ptp(x)
            xs = np.linspace(x.min() - pad, x.max() + pad, 500)
            ax.plot(xs, stats.norm.pdf(xs, x.mean(), x.std(ddof=1)), color=CYAN, lw=1.8,
                    label=f"normal fit (μ={fmt(x.mean(), 4)}, s={fmt(x.std(ddof=1), 4)})")
            try:
                ax.plot(xs, stats.gaussian_kde(x)(xs), color=WARN, lw=1.5, ls="--", label="KDE")
            except Exception:
                pass
        self.style_ax(ax, f"Histogram - {self.v_x.get()}", self.v_x.get(), "density")
        self.style_legend(ax)

    def p_hist_fit(self, ax):
        x, _, _ = self.get_x()
        self.upd_fit()
        fits = self.fits or []
        ax.hist(x, bins=self.hist_edges(x), density=True, color=ACCENT, alpha=0.45, edgecolor=BG,
                label=f"data (n = {len(x)})")
        pad = 0.15 * np.ptp(x)
        xs = np.linspace(x.min() - pad, x.max() + pad, 500)
        for r, col in zip(fits[:3], (CYAN, WARN, "#b48cff")):
            with np.errstate(all="ignore"):
                ax.plot(xs, r["dist"].pdf(xs, *r["params"]), color=col, lw=1.8,
                        label=f"{r['name']}  (AIC {fmt(r['aic'], 5)})")
        self.style_ax(ax, f"Best fitted distributions - {self.v_x.get()}", self.v_x.get(), "density")
        self.style_legend(ax)

    def p_box(self, ax):
        x, _, _ = self.get_x()
        kw = dict(widths=0.5, patch_artist=True, showmeans=True,
                  boxprops=dict(facecolor=SEL, color=ACCENT), medianprops=dict(color=CYAN, lw=2),
                  whiskerprops=dict(color=ACCENT), capprops=dict(color=ACCENT),
                  flierprops=dict(marker="o", markerfacecolor=ERR, markeredgecolor=ERR, markersize=5),
                  meanprops=dict(marker="D", markerfacecolor=WARN, markeredgecolor=WARN))
        try:
            ax.boxplot(x, orientation="horizontal", **kw)
        except TypeError:  # matplotlib < 3.10
            ax.boxplot(x, vert=False, **kw)
        rng = np.random.default_rng(1)
        ax.scatter(x, 1 + rng.uniform(-0.16, 0.16, len(x)), s=9, color=FG, alpha=0.35, zorder=3)
        self.style_ax(ax, f"Box plot - {self.v_x.get()}   (◆ = mean, whiskers = 1.5×IQR)", self.v_x.get())
        ax.set_yticks([])

    def p_box_all(self, ax):
        cols = list(self.df.columns)
        data = [clean(self.df[c]) for c in cols]
        ax.boxplot(data, patch_artist=True, showmeans=True,
                   boxprops=dict(facecolor=SEL, color=ACCENT), medianprops=dict(color=CYAN, lw=2),
                   whiskerprops=dict(color=ACCENT), capprops=dict(color=ACCENT),
                   flierprops=dict(marker="o", markerfacecolor=ERR, markeredgecolor=ERR, markersize=4),
                   meanprops=dict(marker="D", markerfacecolor=WARN, markeredgecolor=WARN))
        ax.set_xticks(range(1, len(cols) + 1))
        ax.set_xticklabels([str(c)[:14] for c in cols], rotation=25 if len(cols) > 5 else 0)
        self.style_ax(ax, "Box plots - all columns", None, "value")

    def p_qq(self, ax):
        x, _, _ = self.get_x()
        (osm, osr), (slope, icpt, r) = stats.probplot(x, dist="norm")
        ax.scatter(osm, osr, s=16, color=ACCENT, alpha=0.85, label="sample quantiles")
        xs = np.array([osm.min(), osm.max()])
        ax.plot(xs, slope * xs + icpt, color=CYAN, lw=1.8, label=f"reference line (R² = {fmt(r * r, 5)})")
        self.style_ax(ax, f"Normal Q-Q plot - {self.v_x.get()}", "theoretical quantiles (z)", "sample quantiles")
        self.style_legend(ax)

    def p_ecdf(self, ax):
        x, _, _ = self.get_x()
        n = len(x)
        xs = np.sort(x)
        ys = np.arange(1, n + 1) / n
        ax.step(xs, ys, where="post", color=ACCENT, lw=1.8, label="empirical CDF")
        if n > 1 and np.ptp(x) > 0:
            g = np.linspace(xs[0] - 0.1 * np.ptp(x), xs[-1] + 0.1 * np.ptp(x), 400)
            ax.plot(g, stats.norm.cdf(g, x.mean(), x.std(ddof=1)), color=CYAN, lw=1.6, label="normal CDF (fitted)")
            eps = math.sqrt(math.log(2 / self.alpha()) / (2 * n))
            ax.fill_between(xs, np.clip(ys - eps, 0, 1), np.clip(ys + eps, 0, 1), step="post", color=ACCENT,
                            alpha=0.12, label=f"DKW {(1 - self.alpha()) * 100:g}% band")
        self.style_ax(ax, f"Empirical CDF - {self.v_x.get()}", self.v_x.get(), "F(x)")
        self.style_legend(ax)

    def p_run(self, ax):
        x, rows, _ = self.get_x()
        m, s = x.mean(), x.std(ddof=1) if len(x) > 1 else 0.0
        ax.plot(rows, x, color=ACCENT, lw=1, marker="o", ms=4)
        ax.axhline(m, color=CYAN, lw=1.6, label=f"mean = {fmt(m, 5)}")
        for k, ls in ((1, ":"), (2, "--"), (3, "-")):
            ax.axhline(m + k * s, color=WARN if k == 3 else DIM, ls=ls, lw=1, label=f"±{k}s" if k > 0 else None)
            ax.axhline(m - k * s, color=WARN if k == 3 else DIM, ls=ls, lw=1)
        if s > 0:
            out = np.abs(x - m) > 3 * s
            ax.scatter(rows[out], x[out], s=40, color=ERR, zorder=4, label="beyond 3s")
        self.style_ax(ax, f"Run sequence - {self.v_x.get()}", "observation (row)", self.v_x.get())
        self.style_legend(ax)

    def p_scatter(self, ax):
        x, y, _ = self.get_xy()
        txt, d = regression(x, y, self.alpha())
        ax.scatter(x, y, s=22, color=ACCENT, alpha=0.8, label=f"data (n = {len(x)})")
        xs = np.linspace(x.min(), x.max(), 200)
        yh = d["b0"] + d["b1"] * xs
        ax.plot(xs, yh, color=CYAN, lw=2, label=f"y = {fmt(d['b0'], 4)} + {fmt(d['b1'], 4)}·x   (R² = {fmt(d['r2'], 4)})")
        h = d["tc"] * d["s"] * np.sqrt(1 / d["n"] + (xs - d["xm"]) ** 2 / d["sxx"])
        hp = d["tc"] * d["s"] * np.sqrt(1 + 1 / d["n"] + (xs - d["xm"]) ** 2 / d["sxx"])
        ax.fill_between(xs, yh - h, yh + h, color=CYAN, alpha=0.18, label=f"{(1 - self.alpha()) * 100:g}% CI (mean)")
        ax.plot(xs, yh - hp, color=WARN, ls="--", lw=1, label=f"{(1 - self.alpha()) * 100:g}% prediction band")
        ax.plot(xs, yh + hp, color=WARN, ls="--", lw=1)
        self.style_ax(ax, f"{self.v_y.get()} vs {self.v_x.get()}", self.v_x.get(), self.v_y.get())
        self.style_legend(ax)

    def p_resid(self, ax):
        x, y, _ = self.get_xy()
        _, d = regression(x, y, self.alpha())
        ax.scatter(d["yhat"], d["res"], s=22, color=ACCENT, alpha=0.8)
        ax.axhline(0, color=CYAN, lw=1.5)
        self.style_ax(ax, "Residuals vs fitted values", "fitted ŷ", "residual  y − ŷ")

    def p_heat(self, ax):
        cols = list(self.df.columns)
        if len(cols) < 2:
            raise ValueError("The heat map needs at least two numeric columns.")
        c, R, _, _, _ = corr_report(self.df, "pearson", self.alpha())
        from matplotlib.colors import LinearSegmentedColormap
        cmap = LinearSegmentedColormap.from_list("sl", [CYAN, PANEL, WARN])
        im = ax.imshow(R, cmap=cmap, vmin=-1, vmax=1)
        ax.set_xticks(range(len(c)))
        ax.set_yticks(range(len(c)))
        ax.set_xticklabels([str(v)[:12] for v in c], rotation=35, ha="right")
        ax.set_yticklabels([str(v)[:12] for v in c])
        for i in range(len(c)):
            for j in range(len(c)):
                if np.isfinite(R[i, j]):
                    ax.text(j, i, f"{R[i, j]:.2f}", ha="center", va="center", color=FG, fontsize=9)
        self.style_ax(ax, "Pearson correlation matrix")
        ax.grid(False)
        cb = self.fig_main.colorbar(im, ax=ax, fraction=0.046)
        cb.ax.tick_params(colors=FG, labelsize=8)
        cb.outline.set_edgecolor(BORDER)

    def save_fig(self, fig):
        p = filedialog.asksaveasfilename(title="Save image", defaultextension=".png",
                                         filetypes=[("PNG", "*.png"), ("SVG", "*.svg"), ("PDF", "*.pdf")])
        if p:
            try:
                fig.savefig(p, facecolor=fig.get_facecolor(), dpi=200)
                self.set_status(f"Saved {p}")
            except Exception as e:
                messagebox.showerror("Save failed", str(e))

    # ------------------------------------------------------------------ tests
    def on_test_change(self, *_):
        m = TEST_META[self.v_test.get()]
        st = lambda w, on: w.configure(state="normal" if on else "disabled")
        st(self.e_mu0, m.mu0)
        st(self.e_s1, m.sigma)
        st(self.e_s2, m.sigma2)
        name = self.v_test.get()
        self.lbl_mu0.configure(text="Δ0 / μ0  (hypothesised)" if m.needs_y else "μ0  (hypothesised)")
        self.lbl_s1.configure(text="σ0  (std dev under H0)" if name.startswith("Chi") else
                              ("σ_X  (known)" if m.sigma2 else "σ  (known)"))
        self.lbl_hint.configure(text=m.hint + ("   Needs Y." if m.needs_y else ""))

    def run_selected_test(self):
        out = self.t_test
        try:
            alpha = self.alpha()
            name = self.v_test.get()
            meta = TEST_META[name]
            alt = self.v_alt.get()
            x, _, _ = self.get_x()
            y = pair = None
            if meta.needs_y:
                xa, ya, _ = self.get_xy()
                pair = (xa, ya)
                y = clean(self.df[self.v_y.get()])
            groups = [clean(self.df[c]) for c in self.df.columns]
            mu0 = self.fnum(self.v_mu0.get(), "μ0") if meta.mu0 else 0.0
            s1 = self.fnum(self.v_s1.get(), "σ") if meta.sigma else 1.0
            s2 = self.fnum(self.v_s2.get(), "σ_Y") if meta.sigma2 else 1.0
            txt = run_test(name, x, y, alpha, alt, mu0, s1, s2, groups, pair, names=[str(c) for c in self.df.columns])
            self.set_text(out, f"X = {self.v_x.get()}" + (f",  Y = {self.v_y.get()}" if meta.needs_y else "")
                          + f",  α = {alpha:g}\n\n" + txt)
        except Exception as e:
            self.set_text(out, f"ERROR: {e}")
            self.set_status(str(e), err=True)

    # -------------------------------------------------------------- relations
    def run_relations(self, silent: bool = False):
        if self.df is None:
            return
        try:
            alpha = self.alpha()
            method = self.v_cm.get()
            cols, R, P, N, COV = corr_report(self.df, method, alpha)
            L = [f"CORRELATION MATRIX  ({method})", fmt_matrix(cols, R), "",
                 "P-VALUES  (H0: no association)", fmt_matrix(cols, P, digits=3), "",
                 "COVARIANCE MATRIX  (sample, pairwise-complete)", fmt_matrix(cols, COV, digits=5), ""]
            cx, cy = self.v_x.get(), self.v_y.get()
            if cy not in ("", "(none)") and cy in self.df.columns and cy != cx:
                x, y, _ = pair_clean(self.df, cx, cy)
                L += [f"PAIR  {cx}  vs  {cy}   (n = {len(x)} complete pairs)", "=" * 40]
                if len(x) >= 4 and np.ptp(x) > 0 and np.ptp(y) > 0:
                    r, p = stats.pearsonr(x, y)
                    z, se = math.atanh(r) if abs(r) < 1 else float("inf"), 1 / math.sqrt(len(x) - 3)
                    zc = stats.norm.ppf(1 - alpha / 2)
                    L.append(f"Pearson  r = {fmt(r)}   p {_peq(p)}   "
                             f"{(1 - alpha) * 100:g}% CI (Fisher z): ({fmt(math.tanh(z - zc * se))} , "
                             f"{fmt(math.tanh(z + zc * se))})")
                    rs, ps = stats.spearmanr(x, y)
                    kt, pk = stats.kendalltau(x, y)
                    L += [f"Spearman ρ = {fmt(rs)}   p {_peq(ps)}",
                          f"Kendall  τ = {fmt(kt)}   p {_peq(pk)}",
                          f"Covariance = {fmt(float(np.cov(x, y, ddof=1)[0, 1]))}", ""]
                x0 = None
                if self.v_x0.get().strip():
                    x0 = self.fnum(self.v_x0.get(), "x0")
                txt, _ = regression(x, y, alpha, x0)
                L.append(txt)
            else:
                L.append("(Choose different X and Y variables in the top bar to get pair statistics and "
                         "linear regression.)")
            self.set_text(self.t_rel, "\n".join(L))
        except Exception as e:
            self.set_text(self.t_rel, f"ERROR: {e}")
            if not silent:
                self.set_status(str(e), err=True)

    # ------------------------------------------------------------ probability
    def build_params(self, *_):
        for w in self.param_frame.winfo_children():
            w.destroy()
        spec = DIST_BY_NAME[self.v_dist.get()]
        self.pvars = []
        for i, (lab, default) in enumerate(spec.params):
            ttk.Label(self.param_frame, text=lab, style="Dim.TLabel").grid(row=i, column=0, sticky="w", pady=3)
            v = tk.StringVar(value=fmt(default, 12))
            e = ttk.Entry(self.param_frame, textvariable=v, width=14)
            e.grid(row=i, column=1, padx=8, pady=3)
            e.bind("<Return>", lambda ev: self.compute_prob())
            self.pvars.append(v)
        self.lbl_note.configure(text=spec.note)
        if spec.discrete:
            self.v_px.set("3")
            self.v_pa.set("2")
            self.v_pb.set("5")
            self.v_pp.set("0.95")
        elif spec.name in ("Normal", "Student t"):
            self.v_px.set("1")
            self.v_pa.set("-1")
            self.v_pb.set("1")
        else:
            self.v_px.set("1")
            self.v_pa.set("0.5")
            self.v_pb.set("2")
        self.compute_prob()

    def use_estimates(self):
        try:
            spec = DIST_BY_NAME[self.v_dist.get()]
            if spec.estimator is None:
                raise ValueError(f"No automatic estimator for {spec.name}; enter the parameters manually.")
            x, _, _ = self.get_x()
            if len(x) < 2:
                raise ValueError("Need at least 2 observations.")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                est = spec.estimator(x)
            if not all(np.isfinite(est)):
                raise ValueError("Estimation failed for this data (check the support of the distribution).")
            for v, val in zip(self.pvars, est):
                v.set(fmt(float(val), 12))
            q1, q3 = (float(v) for v in np.quantile(x, [0.25, 0.75]))
            if spec.discrete:
                self.v_px.set(fmt(round(float(x.mean())), 12))
                self.v_pa.set(fmt(math.floor(q1), 12))
                self.v_pb.set(fmt(math.ceil(q3), 12))
            else:
                self.v_px.set(fmt(float(x.mean()), 8))
                self.v_pa.set(fmt(q1, 8))
                self.v_pb.set(fmt(q3, 8))
            self.compute_prob()
            self.set_status(f"{spec.name} parameters estimated from {self.v_x.get()}.")
        except Exception as e:
            messagebox.showerror("Estimate", str(e))

    def compute_prob(self):
        try:
            spec = DIST_BY_NAME[self.v_dist.get()]
            params = [self.fnum(v.get(), lab) for v, (lab, _) in zip(self.pvars, spec.params)]
            opt = lambda s, n: self.fnum(s.get(), n) if s.get().strip() else None
            x, a, b, p = opt(self.v_px, "x"), opt(self.v_pa, "a"), opt(self.v_pb, "b"), opt(self.v_pp, "p")
            txt, d = prob_calc(spec, params, x, a, b, p)
            if self.df is not None:
                try:
                    xs, _, _ = self.get_x()
                    emp = empirical_report(xs, x, a, b, p)
                    if emp:
                        txt += "\n\n" + emp
                except ValueError:
                    pass
            self.set_text(self.t_prob, txt)
            self.draw_prob(spec, d, x, a, b, p)
        except Exception as e:
            self.set_text(self.t_prob, f"ERROR: {e}")

    def draw_prob(self, spec, d, x, a, b, p):
        fig = self.fig_prob
        fig.clear()
        ax1, ax2 = fig.add_subplot(121), fig.add_subplot(122)
        has_ab = a is not None and b is not None
        lo_ab, hi_ab = (min(a, b), max(a, b)) if has_ab else (None, None)
        if spec.discrete:
            lo = int(d.ppf(0.0005))
            hi = min(max(int(d.ppf(0.9995)), lo + 1), lo + 400)
            ks = np.arange(lo, hi + 1)
            cols = [ACCENT if (has_ab and lo_ab <= k <= hi_ab) else "#3b5a52" for k in ks]
            ax1.bar(ks, d.pmf(ks), color=cols, width=0.8)
            ax2.step(ks, d.cdf(ks), where="post", color=CYAN, lw=1.8)
            self.style_ax(ax1, "PMF", "k", "P(X = k)")
        else:
            lo, hi = float(d.ppf(0.0005)), float(d.ppf(0.9995))
            xs = np.linspace(lo, hi, 600)
            ax1.plot(xs, d.pdf(xs), color=CYAN, lw=1.8)
            if has_ab:
                m = (xs >= lo_ab) & (xs <= hi_ab)
                ax1.fill_between(xs[m], d.pdf(xs[m]), color=ACCENT, alpha=0.5)
            ax2.plot(xs, d.cdf(xs), color=CYAN, lw=1.8)
            self.style_ax(ax1, "PDF   (shaded: a ≤ X ≤ b)", "x", "f(x)")
        self.style_ax(ax2, "CDF", "x", "F(x)")
        if x is not None:
            for ax in (ax1, ax2):
                ax.axvline(x, color=WARN, ls="--", lw=1)
        if p is not None and 0 < p < 1:
            ax2.axhline(p, color=ERR, ls=":", lw=1)
        try:
            fig.tight_layout()
        except Exception:
            pass
        self.canvas_prob.draw_idle()

    # ----------------------------------------------------------------- export
    def export_all(self):
        if self.df is None:
            return
        self.upd_all()
        cols, order, per = self._all_cache
        data = {c: [fmt(per[c][k]) if k in per[c] else "" for k in order] for c in cols}
        out = pd.DataFrame(data, index=[f"{g}: {n}" for g, n in order])
        out.index.name = "Statistic"
        p = filedialog.asksaveasfilename(title="Export statistics table", defaultextension=".csv",
                                         filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx")])
        if not p:
            return
        try:
            if p.lower().endswith(".xlsx"):
                out.to_excel(p)
            else:
                out.to_csv(p, encoding="utf-8-sig")
            self.set_status(f"Saved {p}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    def build_report(self) -> str:
        x, rows, nm = self.get_x()
        a = self.alpha()
        sep = "=" * 78
        L = [sep, f"{APP_NAME} v{APP_VERSION} - statistical report", sep,
             f"Source   : {self.source}", f"Variable : {self.v_x.get()}   (n = {len(x)}, missing = {nm})",
             f"alpha    : {a:g}   confidence = {(1 - a) * 100:g}%   quantile method = {self.v_qm.get()}", ""]
        L += ["DESCRIPTIVE STATISTICS", "-" * 78]
        last = None
        for g, name, val, note in describe(x, nm, 1 - a, self.trim(), self.v_qm.get()):
            if g != last:
                L.append(f"[{g}]")
                last = g
            L.append(f"  {name:<46}{fmt(val):<26}{note}")
        L += ["", "FREQUENCY TABLE", "-" * 78]
        try:
            p = float(self.v_fp.get().replace(",", "."))
        except ValueError:
            p = None
        cols, frows, info = frequency_table(x, self.v_fm.get(), p)
        L.append(info)
        L.append("  ".join(f"{c:<16}" for c in cols))
        for r in frows:
            L.append("  ".join(f"{(fmt(v) if not isinstance(v, str) else v):<16}" for v in r))
        L += ["", stem_and_leaf(x), "", "NORMALITY TESTS", "-" * 78]
        for name, stat, pv, dec, note in normality_tests(x, a):
            L.append(f"  {name:<34}{stat:<34}p = {fmt_p(pv):<10} {dec}")
        L += ["", "OUTLIERS", "-" * 78]
        for k, (desc, pts) in outlier_report(x, rows, a, self.v_qm.get()).items():
            L.append(f"  {k}: {desc}")
            L.append("     " + (", ".join(f"row {int(r)} = {fmt(v)}" for r, v in pts[:60]) if pts else "none"))
        try:
            fits = fit_distributions(x)
            L += ["", "DISTRIBUTION FIT  (ranked by AIC)", "-" * 78]
            for i, r in enumerate(fits, 1):
                L.append(f"  {i:>2}. {r['name']:<14}{r['pretty']:<44}AIC={fmt(r['aic'])}  KS p={fmt_p(r['ksp'])}")
        except ValueError:
            pass
        if len(self.df.columns) > 1:
            cols, R, P, _, _ = corr_report(self.df, self.v_cm.get(), a)
            L += ["", f"CORRELATION MATRIX ({self.v_cm.get()})", "-" * 78, fmt_matrix(cols, R)]
        return "\n".join(L) + "\n"

    def export_report(self):
        if self.df is None:
            messagebox.showinfo("Export", "Load data first.")
            return
        p = filedialog.asksaveasfilename(title="Export report", defaultextension=".txt",
                                         filetypes=[("Text report", "*.txt")])
        if not p:
            return
        try:
            self.config(cursor="watch")
            self.update_idletasks()
            with open(p, "w", encoding="utf-8") as f:
                f.write(self.build_report())
            self.set_status(f"Report saved: {p}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))
        finally:
            self.config(cursor="")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]) else None
    app = StatLab(path)
    app.mainloop()


if __name__ == "__main__":
    main()
