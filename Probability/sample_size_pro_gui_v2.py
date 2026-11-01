#!/usr/bin/env python3
"""
Sample Size Calculator v2 - powerful GUI (tkinter, standard library only)

Core maths is the same as the simple versions (4 cases). On top of it:
  - Solve for: sample size  OR  margin of error (given the sample you can afford)
  - Optional adjustments: non-response rate and design effect (DEFF)
  - Sensitivity tab: table + chart of n against margin of error for 90 / 95 / 99 % confidence
  - History tab: restore, delete, export to CSV
  - Export a text report, copy result, light / dark theme
  - Remembers theme, last inputs and history between sessions
Shortcuts: Enter = save to history, F2 = export report, F3 = theme, Ctrl+R = reset, Ctrl+1/2/3 = tabs
"""
import csv
import json
import math
import os
import tkinter as tk
from datetime import datetime
from pathlib import Path
from statistics import NormalDist
from tkinter import filedialog, messagebox
from tkinter import font as tkfont

# Formulas
# z = critical value, d = margin of error, N = population size, q = 1 - p
#
# 1) Quantitative variable, large population:
#        n = (z * s / d) ^ 2
#
# 2) Quantitative variable, finite population:
#        n = N * z^2 * variance / (d^2 * (N - 1) + z^2 * variance)
#        (variance = s^2, so in this case you enter the variance, not s)
#
# 3) Two-valued variable, large population:
#        n = z^2 * p * q / d^2
#
# 4) Two-valued variable, finite population:
#        n = N * z^2 * p * q / (d^2 * (N - 1) + z^2 * p * q)
#
# Solving for the margin of error instead (n is given):
#        large:  d = z * sqrt(v / n)
#        finite: d = z * sqrt(v * (N - n) / (n * (N - 1)))
#        where v = s^2 (cases 1, 2) or p * q (cases 3, 4)
#
# Adjustments:  n_final = ceil( ceil(n) * DEFF / (1 - non_response) )

CONFIG_PATH = Path(os.environ.get("SAMPLE_SIZE_GUI_CONFIG", Path.home() / ".sample_size_gui.json"))
MAX_HISTORY = 30

# ───────────────────────── themes ─────────────────────────
LIGHT = dict(bg="#f5f5f4", card="#ffffff", border="#e4e4e2", text="#171717", dim="#737373",
             accent="#171717", accent_fg="#ffffff", accent_hover="#000000", soft="#f0f0ee",
             chip="#f0f0ee", chip_hover="#e4e4e2", input_bg="#ffffff", input_off="#f5f5f4",
             sel="#e9e9e6", err="#dc2626", toggle="Dark",
             lines=("#171717", "#737373", "#a3a3a0", "#cfcfcb"))
DARK = dict(bg="#0b0d0e", card="#111416", border="#1f2528", text="#c9d1d3", dim="#6b777b",
            accent="#39ff88", accent_fg="#0b0d0e", accent_hover="#2fd673", soft="#143022",
            chip="#161b1d", chip_hover="#1f2528", input_bg="#0b0d0e", input_off="#0f1214",
            sel="#143022", err="#ff5c5c", toggle="Light",
            lines=("#39ff88", "#2fb5b5", "#c9d1d3", "#6b777b"))

# ───────────────────────── cases ─────────────────────────
CASES = {"1": ("quant", "large"), "2": ("quant", "finite"),
         "3": ("prop", "large"), "4": ("prop", "finite")}
CASE_OF = {v: k for k, v in CASES.items()}
TITLES = {"1": "Quantitative · Large population", "2": "Quantitative · Finite population",
          "3": "Two-valued · Large population", "4": "Two-valued · Finite population"}
CSV_FIELDS = ["result", "solved_for", "case", "variable", "population", "confidence_pct", "z",
              "spread_name", "spread_value", "margin_of_error_or_n", "population_size",
              "nonresponse_pct", "design_effect"]


def frac(num, den, lhs="n =", rhs=""):
    """Draw 'lhs num/den' as a three-line fraction."""
    w = max(len(num), len(den)) + 2
    pad = " " * (len(lhs) + 1)
    return f"{pad}{num.center(w)}\n{lhs} {'─' * w}{rhs}\n{pad}{den.center(w)}"


FORMULAS = {
    "1": "\nn = (z · s / d)²",
    "2": frac("N · z² · s²", "d² · (N − 1) + z² · s²"),
    "3": frac("z² · p · q", "d²") + "     (q = 1 − p)",
    "4": frac("N · z² · p · q", "d² · (N − 1) + z² · p · q"),
}
FORMULAS_D = {
    "1": "\nd = z · s / √n",
    "2": frac("s² · (N − n)", "n · (N − 1)", "d = z · √(", ")"),
    "3": "\nd = z · √(p · q / n)",
    "4": frac("p · q · (N − n)", "n · (N − 1)", "d = z · √(", ")"),
}


# ───────────────────────── parsing ─────────────────────────
def num(text, pct=False):
    t = text.strip().replace(",", "")
    if not t:
        raise ValueError("Required")
    is_pct = t.endswith("%")
    if is_pct:
        if not pct:
            raise ValueError("Enter a plain number")
        t = t[:-1]
    try:
        v = float(t)
    except ValueError:
        raise ValueError("Enter a number") from None
    if not math.isfinite(v):
        raise ValueError("Enter a number")
    return v / 100 if is_pct else v


def v_conf(text):
    v = num(text, pct=True)
    c = v / 100 if v > 1 else v          # "95", "95%" and "0.95" all mean 95 %
    if not 0 < c < 1:
        raise ValueError("Must be between 0 and 100")
    return c


def v_positive(text):
    v = num(text)
    if v <= 0:
        raise ValueError("Must be greater than 0")
    return v


def v_fraction(text):
    v = num(text, pct=True)
    if not 0 < v < 1:
        raise ValueError("Must be between 0 and 1 (or e.g. 5%)")
    return v


def v_whole(text):
    v = num(text)
    if v < 2 or v != int(v):
        raise ValueError("Whole number, at least 2")
    return int(v)


def v_nonresp(text):
    if not text.strip():
        return 0.0
    v = num(text, pct=True)
    if not text.strip().endswith("%"):
        v /= 100                          # a bare number is a percentage here
    if not 0 <= v < 1:
        raise ValueError("From 0% to below 100%")
    return v


def v_deff(text):
    if not text.strip():
        return 1.0
    v = num(text)
    if v < 1:
        raise ValueError("Must be 1 or more")
    return v


# ───────────────────────── maths ─────────────────────────
def z_value(conf):
    return NormalDist().inv_cdf(1 - (1 - conf) / 2)


def variance_term(case, spread):
    if case == "1":
        return spread ** 2               # spread = s
    if case == "2":
        return spread                    # spread = variance (s^2)
    return spread * (1 - spread)         # spread = p, term = p * q


def size(case, z, spread, d, N):
    v = variance_term(case, spread)
    if case in ("1", "3"):
        n = z ** 2 * v / d ** 2
    else:
        n = N * z ** 2 * v / (d ** 2 * (N - 1) + z ** 2 * v)
    return n, v


def margin(case, z, spread, n_eff, N):
    v = variance_term(case, spread)
    if case in ("1", "3"):
        d = z * math.sqrt(v / n_eff)
    else:
        d = z * math.sqrt(max(0.0, v * (N - n_eff) / (n_eff * (N - 1))))
    return d, v


def ceil_n(x):
    return math.ceil(round(x, 9))        # round() guards against float noise like 385.00000000001


def final_size(case, z, spread, d, N, deff, r):
    n_raw, _ = size(case, z, spread, d, N)
    return ceil_n(ceil_n(n_raw) * deff / (1 - r))


def describe_size(case, z, spread, v, d, N):
    zs = f"{z:.4f}"
    if case == "1":
        return f"s² = {spread:g}² = {v:g}", f"({zs} × {spread:g} / {d:g})²"
    if case == "2":
        return (f"s² = {v:g}",
                f"{N:,} × {zs}² × {v:g} / ({d:g}² × ({N:,} − 1) + {zs}² × {v:g})")
    term = f"p·q = {spread:g} × {1 - spread:g} = {v:.4g}"
    if case == "3":
        return term, f"{zs}² × {v:.4g} / {d:g}²"
    return term, f"{N:,} × {zs}² × {v:.4g} / ({d:g}² × ({N:,} − 1) + {zs}² × {v:.4g})"


def describe_margin(case, z, spread, v, n_eff, N):
    zs, ne = f"{z:.4f}", f"{n_eff:,.2f}"
    if case == "1":
        return f"s² = {spread:g}² = {v:g}", f"{zs} × {spread:g} / √{ne}"
    if case == "2":
        return f"s² = {v:g}", f"{zs} × √({v:g} × ({N:,} − {ne}) / ({ne} × ({N:,} − 1)))"
    term = f"p·q = {spread:g} × {1 - spread:g} = {v:.4g}"
    if case == "3":
        return term, f"{zs} × √({v:.4g} / {ne})"
    return term, f"{zs} × √({v:.4g} × ({N:,} − {ne}) / ({ne} × ({N:,} − 1)))"


def short(v):
    return f"{v / 1000:.0f}k" if v >= 10000 else f"{v:,.0f}"


# ───────────────────────── files ─────────────────────────
def write_text(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:   # utf-8-sig: opens cleanly in Excel
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


# ───────────────────────── widgets ─────────────────────────
class Segmented(tk.Frame):
    """Two-option toggle that looks like a segmented control."""

    def __init__(self, parent, items, var, command, colors, font, px):
        super().__init__(parent, bg=colors["border"], padx=1, pady=1)
        self.var, self.command, self.c = var, command, colors
        self.buttons = {}
        for text, value in items:
            b = tk.Label(self, text=text, font=font, padx=px(9), pady=px(7), cursor="hand2")
            b.pack(side="left", fill="x", expand=True)
            b.bind("<Button-1>", lambda e, v=value: self.select(v))
            b.bind("<Enter>", lambda e, v=value: self.hover(v, True))
            b.bind("<Leave>", lambda e, v=value: self.hover(v, False))
            self.buttons[value] = b
        self.render()

    def select(self, value):
        self.var.set(value)
        self.render()
        self.command()

    def hover(self, value, inside):
        if self.var.get() != value:
            self.buttons[value].config(bg=self.c["chip"] if inside else self.c["card"])

    def render(self):
        for value, b in self.buttons.items():
            on = self.var.get() == value
            b.config(bg=self.c["accent"] if on else self.c["card"],
                     fg=self.c["accent_fg"] if on else self.c["text"])


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sample Size Calculator")
        self.resizable(False, False)
        self.sc = max(1.0, self.winfo_fpixels("1i") / 96)   # DPI scale for paddings
        self.c = LIGHT
        self.tab = "calc"
        self.history = []
        self.current = None
        self.vals = {}
        self.sens_data = None
        self.focus_key = None
        self.scrolling = False

        fams = set(tkfont.families())
        ui = next((f for f in ("Segoe UI", "SF Pro Text", "Helvetica Neue", "Inter", "DejaVu Sans", "Arial")
                   if f in fams), "Helvetica")
        mono = next((f for f in ("Cascadia Mono", "Consolas", "JetBrains Mono", "Menlo", "DejaVu Sans Mono",
                                 "Courier New") if f in fams), "Courier")
        self.F = dict(base=(ui, 10), small=(ui, 9), bold=(ui, 10, "bold"), cap=(ui, 8, "bold"),
                      title=(ui, 19, "bold"), big=(ui, 40, "bold"), mono=(mono, 10), mono_s=(mono, 9),
                      mono_b=(mono, 11))

        self.v_type = tk.StringVar(value="quant")
        self.v_pop = tk.StringVar(value="large")
        self.v_mode = tk.StringVar(value="n")                # "n" = solve for sample size, "d" = for margin
        self.v_conf = tk.StringVar(value="95")
        self.v_s = tk.StringVar(value="10")
        self.v_var = tk.StringVar(value="100")
        self.v_p = tk.StringVar(value="0.5")
        self.v_dq = tk.StringVar(value="1")
        self.v_dp = tk.StringVar(value="0.05")
        self.v_N = tk.StringVar(value="1000")
        self.v_navail = tk.StringVar(value="385")
        self.v_nr = tk.StringVar(value="0")
        self.v_deff = tk.StringVar(value="1")
        self.persist = dict(type=self.v_type, pop=self.v_pop, mode=self.v_mode, conf=self.v_conf, s=self.v_s,
                            var=self.v_var, p=self.v_p, dq=self.v_dq, dp=self.v_dp, N=self.v_N,
                            navail=self.v_navail, nr=self.v_nr, deff=self.v_deff)
        self.modes = {"type": {"quant", "prop"}, "pop": {"large", "finite"}, "mode": {"n", "d"}}
        self.defaults = {k: v.get() for k, v in self.persist.items()}

        self.load_config()
        self.build()
        for k, v in self.persist.items():
            if k not in self.modes:
                v.trace_add("write", self.refresh)

        self.bind("<Return>", lambda e: self.save_history())
        self.bind("<F2>", lambda e: self.export_report())
        self.bind("<F3>", lambda e: self.toggle_theme())
        self.bind("<Control-r>", lambda e: self.reset())
        for i, name in enumerate(("calc", "sens", "hist"), 1):
            self.bind(f"<Control-Key-{i}>", lambda e, n=name: self.show_tab(n))
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind_all(seq, self.on_wheel)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---- small helpers ----
    def px(self, v):
        return round(v * self.sc)

    def case(self):
        return CASE_OF[(self.v_type.get(), self.v_pop.get())]

    def spread_var(self):
        return {"1": self.v_s, "2": self.v_var, "3": self.v_p, "4": self.v_p}[self.case()]

    def d_var(self):
        return self.v_dq if self.case() in ("1", "2") else self.v_dp

    def card(self, parent, title, width=390):
        c, px = self.c, self.px
        outer = tk.Frame(parent, bg=c["border"])
        inner = tk.Frame(outer, bg=c["card"], padx=px(20), pady=px(14))
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Label(inner, text=title.upper(), font=self.F["cap"], fg=c["dim"], bg=c["card"],
                 anchor="w").pack(fill="x", pady=(0, px(10)))
        tk.Frame(inner, width=px(width), height=1, bg=c["card"]).pack()    # fixes the card width
        return outer, inner

    def chip(self, parent, text, command):
        c, px = self.c, self.px
        b = tk.Label(parent, text=text, font=self.F["small"], bg=c["chip"], fg=c["dim"],
                     padx=px(8), pady=px(2), cursor="hand2")
        b.bind("<Button-1>", lambda e: command())
        b.bind("<Enter>", lambda e: b.config(bg=c["chip_hover"], fg=c["text"]))
        b.bind("<Leave>", lambda e: b.config(bg=c["chip"], fg=c["dim"]))
        return b

    def button(self, parent, text, command, primary=False):
        c, px = self.c, self.px
        bg, fg, hov = ((c["accent"], c["accent_fg"], c["accent_hover"]) if primary
                       else (c["card"], c["text"], c["chip"]))
        b = tk.Label(parent, text=text, font=self.F["bold"], bg=bg, fg=fg, padx=px(14), pady=px(7),
                     cursor="hand2", highlightthickness=1,
                     highlightbackground=c["accent"] if primary else c["border"])
        b.base_text = text
        b.bind("<Button-1>", lambda e: command())
        b.bind("<Enter>", lambda e: b.config(bg=hov))
        b.bind("<Leave>", lambda e: b.config(bg=bg))
        return b

    def flash(self, button, text):
        def restore():
            try:
                button.config(text=button.base_text)
            except tk.TclError:          # window or theme was rebuilt in the meantime
                pass

        button.config(text=text)
        self.after(900, restore)

    def make_field(self, parent, key, wrap=370):
        c, F, px = self.c, self.F, self.px
        fr = tk.Frame(parent, bg=c["card"])
        top = tk.Frame(fr, bg=c["card"])
        top.pack(fill="x")
        lab = tk.Label(top, font=F["bold"], fg=c["text"], bg=c["card"], anchor="w")
        lab.pack(side="left")
        chips = tk.Frame(top, bg=c["card"])
        chips.pack(side="right")
        border = tk.Frame(fr, bg=c["border"], padx=1, pady=1)
        border.pack(fill="x", pady=(px(4), 0))
        box = tk.Frame(border, bg=c["input_bg"], padx=px(9), pady=px(5))
        box.pack(fill="x")
        ent = tk.Entry(box, font=F["base"], relief="flat", bd=0, bg=c["input_bg"], fg=c["text"],
                       insertbackground=c["accent"], disabledbackground=c["input_off"],
                       disabledforeground=c["dim"], highlightthickness=0)
        ent.pack(fill="x")
        ent.bind("<FocusIn>", lambda e, k=key: self.set_focus(k))
        ent.bind("<FocusOut>", lambda e: self.set_focus(None))
        msg = tk.Label(fr, font=F["small"], fg=c["dim"], bg=c["card"], anchor="w", justify="left",
                       wraplength=px(wrap))
        msg.pack(fill="x", pady=(px(3), 0))
        self.fields[key] = dict(lab=lab, ent=ent, box=box, wrap=border, msg=msg, chips=chips, error=False)
        return fr

    # ---- layout ----
    def build(self):
        c, F, px = self.c, self.F, self.px
        self.configure(bg=c["bg"])
        self.shell = tk.Frame(self, bg=c["bg"])
        self.shell.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(self.shell, bg=c["bg"], highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(self.shell, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left")
        self.root = tk.Frame(self.canvas, bg=c["bg"], padx=px(28), pady=px(18))
        self.canvas.create_window((0, 0), window=self.root, anchor="nw")
        self.fields = {}
        tk.Frame(self.root, width=px(960), height=1, bg=c["bg"]).pack()    # same width on every tab

        head = tk.Frame(self.root, bg=c["bg"])
        head.pack(fill="x", pady=(0, px(10)))
        titles = tk.Frame(head, bg=c["bg"])
        titles.pack(side="left")
        tk.Label(titles, text="Sample Size Calculator", font=F["title"], fg=c["text"], bg=c["bg"]).pack(anchor="w")
        tk.Label(titles, text="Means and proportions  ·  large or finite populations  ·  adjustments  ·  sensitivity",
                 font=F["base"], fg=c["dim"], bg=c["bg"]).pack(anchor="w", pady=(2, 0))
        self.button(head, "◐  " + c["toggle"], self.toggle_theme).pack(side="right", anchor="n")

        strip = tk.Frame(self.root, bg=c["bg"])
        strip.pack(fill="x", pady=(0, px(10)))
        self.tab_btns = {}
        for name, text in (("calc", "Calculator"), ("sens", "Sensitivity"), ("hist", "History")):
            b = tk.Label(strip, text=text, font=F["bold"], padx=px(16), pady=px(7), cursor="hand2")
            b.pack(side="left", padx=(0, px(4)))
            b.bind("<Button-1>", lambda e, n=name: self.show_tab(n))
            self.tab_btns[name] = b

        host = tk.Frame(self.root, bg=c["bg"])
        host.pack(fill="both", expand=True)
        self.pages = {name: tk.Frame(host, bg=c["bg"]) for name in ("calc", "sens", "hist")}
        self.build_calc(self.pages["calc"])
        self.build_sens(self.pages["sens"])
        self.build_hist(self.pages["hist"])

        tk.Label(self.root, text="Enter  save to history   ·   F2  export report   ·   F3  theme   ·   "
                                 "Ctrl+R  reset   ·   Ctrl+1/2/3  tabs",
                 font=F["small"], fg=c["dim"], bg=c["bg"]).pack(anchor="w", pady=(px(14), 0))
        self.on_mode()
        self.show_tab(self.tab)

    def show_tab(self, name):
        c = self.c
        self.tab = name
        for page in self.pages.values():
            page.pack_forget()
        self.pages[name].pack(fill="both", expand=True)
        for key, b in self.tab_btns.items():
            on = key == name
            b.config(bg=c["accent"] if on else c["bg"], fg=c["accent_fg"] if on else c["dim"])
        self.fit_window()

    def fit_window(self):
        """Size the window to its content; add a scrollbar if the screen is too small."""
        self.update_idletasks()
        w, h = self.root.winfo_reqwidth(), self.root.winfo_reqheight()
        limit = self.winfo_screenheight() - self.px(120)
        self.scrolling = h > limit
        self.canvas.configure(width=w, height=min(h, limit), scrollregion=(0, 0, w, h))
        self.canvas.yview_moveto(0)
        if self.scrolling:
            self.scrollbar.pack(side="right", fill="y")
        else:
            self.scrollbar.pack_forget()

    def on_wheel(self, event):
        if self.scrolling:
            up = event.num == 4 or getattr(event, "delta", 0) > 0
            self.canvas.yview_scroll(-2 if up else 2, "units")

    # ---- calculator page ----
    def build_calc(self, page):
        c, F, px = self.c, self.F, self.px
        left = tk.Frame(page, bg=c["bg"])
        right = tk.Frame(page, bg=c["bg"])
        left.grid(row=0, column=0, sticky="n")
        right.grid(row=0, column=1, sticky="n", padx=(px(18), 0))

        # study design
        outer, inner = self.card(left, "Study design")
        outer.pack(fill="x")
        row = tk.Frame(inner, bg=c["card"])
        row.pack(fill="x", pady=(0, px(14)))
        row.columnconfigure(0, weight=1, uniform="seg")
        row.columnconfigure(1, weight=1, uniform="seg")
        selectors = (("Variable", "seg_type", [("Quantitative", "quant"), ("Two-valued", "prop")], self.v_type),
                     ("Population", "seg_pop", [("Large", "large"), ("Finite", "finite")], self.v_pop))
        for col, (title, attr, items, var) in enumerate(selectors):
            cell = tk.Frame(row, bg=c["card"])
            cell.grid(row=0, column=col, sticky="ew", padx=(0, px(10)) if col == 0 else 0)
            tk.Label(cell, text=title, font=F["bold"], fg=c["text"], bg=c["card"], anchor="w").pack(
                fill="x", pady=(0, px(4)))
            seg = Segmented(cell, items, var, self.on_mode, c, F["base"], px)
            seg.pack(fill="x")
            setattr(self, attr, seg)

        box = tk.Frame(inner, bg=c["soft"], padx=px(14), pady=px(12))
        box.pack(fill="x")
        self.l_case = tk.Label(box, font=F["cap"], fg=c["accent"] if c is DARK else c["dim"],
                               bg=c["soft"], anchor="w")
        self.l_case.pack(fill="x")
        self.l_formula = tk.Label(box, font=F["mono_b"], fg=c["text"], bg=c["soft"], anchor="w",
                                  justify="left", height=3)
        self.l_formula.pack(fill="x", pady=(px(6), px(6)))
        tk.Label(box, text="z: critical value  ·  d: margin of error  ·  N: population size", font=F["small"],
                 fg=c["dim"], bg=c["soft"], anchor="w", justify="left", wraplength=px(362)).pack(fill="x")

        # parameters
        outer, inner = self.card(left, "Parameters")
        outer.pack(fill="x", pady=(px(16), 0))
        for i, key in enumerate(("conf", "spread", "d", "N")):
            self.make_field(inner, key).pack(fill="x", pady=(px(9) if i else 0, 0))
        self.fields["conf"]["ent"].config(textvariable=self.v_conf)
        self.fields["N"]["ent"].config(textvariable=self.v_N)
        for t in ("90", "95", "99"):
            self.chip(self.fields["conf"]["chips"], t + "%", lambda t=t: self.v_conf.set(t)).pack(
                side="left", padx=(px(4), 0))
        self.chip_p = self.chip(self.fields["spread"]["chips"], "p = 0.5", lambda: self.v_p.set("0.5"))
        self.chip_d = [self.chip(self.fields["d"]["chips"], t + "%", lambda t=t: self.v_dp.set(f"0.0{t}"))
                       for t in ("3", "5")]

        # result
        outer, inner = self.card(right, "Result")
        outer.pack(fill="x")
        self.seg_mode = Segmented(inner, [("Solve for sample size", "n"), ("Solve for margin of error", "d")],
                                  self.v_mode, self.on_mode, c, F["small"], px)
        self.seg_mode.pack(fill="x", pady=(0, px(8)))
        self.l_n = tk.Label(inner, text="—", font=F["big"], fg=c["accent"], bg=c["card"], anchor="w")
        self.l_n.pack(fill="x")
        self.l_sub = tk.Label(inner, font=F["base"], fg=c["dim"], bg=c["card"], anchor="w", justify="left",
                              wraplength=px(390))
        self.l_sub.pack(fill="x", pady=(0, px(10)))
        tk.Frame(inner, bg=c["border"], height=1).pack(fill="x", pady=(0, px(8)))

        grid = tk.Frame(inner, bg=c["card"])
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)
        self.step_rows = []
        for i, lines in enumerate((1, 1, 3, 2, 2, 1)):
            name = tk.Label(grid, text="", font=F["small"], fg=c["dim"], bg=c["card"], anchor="nw", width=14)
            name.grid(row=i, column=0, sticky="nw", pady=px(2))
            val = tk.Label(grid, text="—", font=F["mono_s"], fg=c["text"], bg=c["card"], anchor="nw",
                           justify="left", wraplength=px(270), height=lines)
            val.grid(row=i, column=1, sticky="nw", pady=px(2))
            self.step_rows.append((name, val))

        self.l_notes = tk.Label(inner, font=F["small"], fg=c["dim"], bg=c["card"], anchor="nw",
                                justify="left", wraplength=px(390), height=2)
        self.l_notes.pack(fill="x", pady=(px(6), px(10)))

        btns = tk.Frame(inner, bg=c["card"])
        btns.pack(fill="x")
        self.btn_copy = self.button(btns, "Copy", self.copy, primary=True)
        self.btn_copy.pack(side="left")
        self.btn_save = self.button(btns, "Save", self.save_history)
        self.btn_save.pack(side="left", padx=(px(8), 0))
        self.btn_export = self.button(btns, "Export", self.export_report)
        self.btn_export.pack(side="left", padx=(px(8), 0))
        self.button(btns, "Reset", self.reset).pack(side="right")

        # adjustments
        outer, inner = self.card(right, "Adjustments  (optional)")
        outer.pack(fill="x", pady=(px(16), 0))
        two = tk.Frame(inner, bg=c["card"])
        two.pack(fill="x")
        two.columnconfigure(0, weight=1, uniform="adj")
        two.columnconfigure(1, weight=1, uniform="adj")
        for col, key in enumerate(("nr", "deff")):
            self.make_field(two, key, wrap=170).grid(row=0, column=col, sticky="new",
                                                     padx=(0, px(12)) if col == 0 else 0)
        self.fields["nr"]["ent"].config(textvariable=self.v_nr)
        self.fields["deff"]["ent"].config(textvariable=self.v_deff)

    # ---- sensitivity page ----
    def build_sens(self, page):
        c, F, px = self.c, self.F, self.px
        left = tk.Frame(page, bg=c["bg"])
        right = tk.Frame(page, bg=c["bg"])
        left.grid(row=0, column=0, sticky="n")
        right.grid(row=0, column=1, sticky="n", padx=(px(18), 0))

        outer, inner = self.card(left, "Required n by margin of error", width=400)
        outer.pack(fill="x")
        self.sens_msg = tk.Label(inner, font=F["small"], fg=c["dim"], bg=c["card"], anchor="w", justify="left",
                                 wraplength=px(390))
        self.sens_msg.pack(fill="x", pady=(0, px(8)))
        self.sens_table = tk.Frame(inner, bg=c["card"])
        self.sens_table.pack(fill="x")
        tk.Label(inner, text="Uses the current parameters, adjustments and population size. "
                             "The highlighted cell is your current setting.", font=F["small"], fg=c["dim"],
                 bg=c["card"], anchor="w", justify="left", wraplength=px(390)).pack(fill="x", pady=(px(10), px(10)))
        self.button(inner, "Export CSV", self.export_sens).pack(anchor="w")

        outer, inner = self.card(right, "Chart  ·  n vs margin of error", width=410)
        outer.pack(fill="x")
        self.chart = tk.Canvas(inner, width=px(410), height=px(330), bg=c["card"], highlightthickness=0, bd=0)
        self.chart.pack()

    # ---- history page ----
    def build_hist(self, page):
        c, F, px = self.c, self.F, self.px
        outer, inner = self.card(page, "Saved calculations", width=880)
        outer.pack(fill="x")
        box = tk.Frame(inner, bg=c["card"])
        box.pack(fill="x")
        self.hist = tk.Listbox(box, font=F["mono_s"], height=14, relief="flat", bd=0, bg=c["input_bg"],
                               fg=c["text"], highlightthickness=1, highlightbackground=c["border"],
                               highlightcolor=c["border"], selectbackground=c["sel"],
                               selectforeground=c["text"], activestyle="none", exportselection=False)
        sb = tk.Scrollbar(box, command=self.hist.yview)
        self.hist.config(yscrollcommand=sb.set)
        self.hist.pack(side="left", fill="x", expand=True)
        sb.pack(side="right", fill="y")
        self.hist.bind("<Double-Button-1>", self.restore)
        self.fill_history()

        btns = tk.Frame(inner, bg=c["card"])
        btns.pack(fill="x", pady=(px(14), 0))
        self.button(btns, "Restore", self.restore, primary=True).pack(side="left")
        self.button(btns, "Delete", self.delete_history).pack(side="left", padx=(px(8), 0))
        self.button(btns, "Export CSV", self.export_history).pack(side="left", padx=(px(8), 0))
        self.button(btns, "Clear all", self.clear_history).pack(side="right")
        tk.Label(inner, text="Double-click a row to restore its inputs on the Calculator tab.", font=F["small"],
                 fg=c["dim"], bg=c["card"]).pack(anchor="w", pady=(px(10), 0))

    def fill_history(self):
        self.hist.delete(0, "end")
        for h in self.history:
            self.hist.insert("end", h["line"])

    # ---- mode / labels ----
    def on_mode(self):
        c, px = self.c, self.px
        case, mode = self.case(), self.v_mode.get()
        quant, finite = case in ("1", "2"), case in ("2", "4")
        f = self.fields

        for seg in (self.seg_type, self.seg_pop, self.seg_mode):
            seg.render()
        self.l_case.config(text=f"CASE {case}  ·  {TITLES[case].upper()}"
                                + ("  ·  SOLVING FOR d" if mode == "d" else ""))
        self.l_formula.config(text=(FORMULAS if mode == "n" else FORMULAS_D)[case])

        f["conf"]["lab"].config(text="Confidence level (%)")
        f["spread"]["lab"].config(text={"1": "Standard deviation (s)", "2": "Variance (s²)",
                                        "3": "Proportion (p)", "4": "Proportion (p)"}[case])
        f["d"]["lab"].config(text="Margin of error (d)" if mode == "n" else "Sample size available (n)")
        f["N"]["lab"].config(text="Population size (N)", fg=c["text"] if finite else c["dim"])
        f["nr"]["lab"].config(text="Non-response (%)")
        f["deff"]["lab"].config(text="Design effect (DEFF)")
        f["spread"]["ent"].config(textvariable=self.spread_var())
        f["d"]["ent"].config(textvariable=self.d_var() if mode == "n" else self.v_navail)
        f["N"]["ent"].config(state="normal" if finite else "disabled")
        f["N"]["box"].config(bg=c["input_bg"] if finite else c["input_off"])

        for chip in [self.chip_p, *self.chip_d]:
            chip.pack_forget()
        if not quant:
            self.chip_p.pack(side="left", padx=(px(4), 0))
            if mode == "n":
                for chip in self.chip_d:
                    chip.pack(side="left", padx=(px(4), 0))

        self.hints = {
            "conf": "Typical: 90, 95 or 99   ·   also accepts 0.95 or 95%",
            "spread": {"1": "Population standard deviation (pilot study or literature)",
                       "2": "Enter the variance (s²), not the standard deviation",
                       "3": "Expected proportion   ·   0.5 if unknown (gives the largest n)",
                       "4": "Expected proportion   ·   0.5 if unknown (gives the largest n)"}[case],
            "d": (("Absolute error, in the same unit as the variable" if quant
                   else "Absolute error   ·   0.05 or 5% means ±5 percentage points") if mode == "n"
                  else "Planned sample, before non-response and design effect"),
            "N": ("Total number of units in the population" if finite else "Not used for a large population"),
            "nr": "0 = no non-response",
            "deff": "1 = simple random",
        }
        self.refresh()

    def set_focus(self, key):
        self.focus_key = key
        for k in self.fields:
            self.paint_border(k)

    def paint_border(self, key):
        f = self.fields[key]
        if f["error"]:
            col = self.c["err"]
        elif self.focus_key == key:
            col = self.c["accent"]
        else:
            col = self.c["border"]
        f["wrap"].config(bg=col)

    def set_msg(self, key, text, error):
        f = self.fields[key]
        f["error"] = error
        f["msg"].config(text=text, fg=self.c["err"] if error else self.c["dim"])
        self.paint_border(key)

    def set_empty(self):
        self.current = None
        self.l_n.config(text="—", fg=self.c["dim"])
        self.l_sub.config(text="Fix the highlighted field to see the result.")
        names = (("z", "Variance term", "Substitution", "Base n", "Adjusted n", "n / N") if self.v_mode.get() == "n"
                 else ("z", "Variance term", "Substitution", "Effective n", "Margin of error", "n / N"))
        for (name, val), text in zip(self.step_rows, names):
            name.config(text=text)
            val.config(text="—")
        self.l_notes.config(text="")

    # ---- main calculation ----
    def refresh(self, *_):
        case, mode = self.case(), self.v_mode.get()
        quant, finite = case in ("1", "2"), case in ("2", "4")

        spec = [("conf", self.v_conf, v_conf),
                ("spread", self.spread_var(), v_positive if quant else v_fraction),
                ("nr", self.v_nr, v_nonresp), ("deff", self.v_deff, v_deff)]
        if mode == "n":
            spec.append(("d", self.d_var(), v_positive if quant else v_fraction))
        else:
            spec.append(("d", self.v_navail, v_whole))
        if finite:
            spec.append(("N", self.v_N, v_whole))

        vals, bad = {}, set()
        for key, var, check in spec:
            try:
                vals[key] = check(var.get())
                self.set_msg(key, self.hints[key], False)
            except ValueError as e:
                bad.add(key)
                self.set_msg(key, str(e), True)
        if not finite:
            self.set_msg("N", self.hints["N"], False)
        if mode == "d" and finite and "d" in vals and "N" in vals and vals["d"] > vals["N"]:
            bad.add("d")
            self.set_msg("d", "Must not exceed N", True)

        self.vals = vals
        self.update_sensitivity()
        if bad:
            self.set_empty()
            return

        conf, spread, r, deff = vals["conf"], vals["spread"], vals["nr"], vals["deff"]
        N = vals.get("N")
        z = z_value(conf)
        adjusted = deff != 1 or r > 0
        sp_name = {"1": "Standard deviation (s)", "2": "Variance (s²)",
                   "3": "Proportion (p)", "4": "Proportion (p)"}[case]
        sp = {"1": f"s = {spread:g}", "2": f"s² = {spread:g}", "3": f"p = {spread:g}", "4": f"p = {spread:g}"}[case]
        tail = (f"  NR={r * 100:g}%" if r > 0 else "") + (f"  DEFF={deff:g}" if deff != 1 else "")
        adj_txt = ((f", non-response {r * 100:g}%" if r > 0 else "") + (f", DEFF {deff:g}" if deff != 1 else ""))
        notes = []

        if mode == "n":
            d = vals["d"]
            n_raw, v = size(case, z, spread, d, N)
            n_base = ceil_n(n_raw)
            n_adj_raw = n_base * deff / (1 - r)
            n_final = ceil_n(n_adj_raw)
            term, sub = describe_size(case, z, spread, v, d, N)
            res_text = f"{n_final:,}"
            sub_text = ("units needed in the sample, after adjustments" if adjusted
                        else "units needed in the sample (always rounded up)")
            steps = [("z", f"{z:.4f}   ({conf * 100:g}% confidence)"), ("Variance term", term),
                     ("Substitution", sub), ("Base n", f"{n_raw:,.2f}  →  {n_base:,}"),
                     ("Adjusted n", (f"{n_base:,} × {deff:g} ÷ {1 - r:.2f} = {n_adj_raw:,.2f}  →  {n_final:,}"
                                     if adjusted else "no adjustments")),
                     ("n / N", f"{n_final / N:.1%}" if finite else "—")]
            d_label = f"{d:g}"
            params = [("Confidence level", f"{conf * 100:g}%  (z = {z:.4f})"), (sp_name, f"{spread:g}"),
                      ("Margin of error (d)", d_label)]
            summary_head = f"Sample size n = {res_text}"
            line = f"{res_text:>9}  C{case}  {conf * 100:g}%  {sp}  d={d:g}"
            input_value, result_value = d, n_final
            if finite and n_final >= N:
                notes.append("n reaches N: survey the whole population (census).")
            elif finite and (z * z * v / (d * d)) / N < 0.05:
                notes.append("Finite-population correction is negligible here (n₀ / N < 5%).")
            elif not finite:
                notes.append("If n would exceed 5% of N, switch to a finite population.")
            frac_n = n_final
        else:
            n_in = vals["d"]
            n_eff = n_in * (1 - r) / deff
            d_res, v = margin(case, z, spread, n_eff, N)
            term, sub = describe_margin(case, z, spread, v, n_eff, N)
            shown = f"± {d_res * 100:.2f}%" if not quant else f"± {d_res:.4g}"
            res_text = shown
            sub_text = f"margin of error with n = {n_in:,}" + (" (after adjustments)" if adjusted else "")
            steps = [("z", f"{z:.4f}   ({conf * 100:g}% confidence)"), ("Variance term", term),
                     ("Substitution", sub),
                     ("Effective n", (f"{n_in:,} × {1 - r:.2f} ÷ {deff:g} = {n_eff:,.2f}" if adjusted
                                      else f"{n_eff:,.2f}")),
                     ("Margin of error", (f"± {d_res * 100:.3f} percentage points" if not quant
                                          else f"± {d_res:.5g}")),
                     ("n / N", f"{n_in / N:.1%}" if finite else "—")]
            params = [("Confidence level", f"{conf * 100:g}%  (z = {z:.4f})"), (sp_name, f"{spread:g}"),
                      ("Sample size available (n)", f"{n_in:,}")]
            summary_head = f"Margin of error = {res_text}"
            line = f"{res_text:>9}  C{case}  {conf * 100:g}%  {sp}  n={n_in:,}"
            input_value, result_value = n_in, d_res
            if finite and n_in >= N:
                notes.append("n equals N: a census has no sampling error.")
            if adjusted:
                notes.append("Effective n = n × (1 − non-response) ÷ DEFF.")
            frac_n = n_in
        if finite:
            params.append(("Population size (N)", f"{N:,}"))
            line += f"  N={N:,}"
        params += [("Non-response", f"{r * 100:g}%"), ("Design effect (DEFF)", f"{deff:g}")]
        line += tail

        self.l_n.config(text=res_text, fg=self.c["accent"])
        self.l_sub.config(text=sub_text)
        for (name, val), (label, text) in zip(self.step_rows, steps):
            name.config(text=label)
            val.config(text=text)
        self.l_notes.config(text="  ".join(notes))

        formula = (FORMULAS if mode == "n" else FORMULAS_D)[case].strip("\n")
        report = "\n".join([
            "SAMPLE SIZE REPORT", "=" * 44,
            f"Generated     {datetime.now():%Y-%m-%d %H:%M}",
            f"Design        {TITLES[case]}  (case {case})",
            f"Solving for   {'Sample size' if mode == 'n' else 'Margin of error'}",
            "", "Formula", *["  " + ln for ln in formula.splitlines()],
            "", "Inputs", *[f"  {k:<26}{val}" for k, val in params],
            "", "Calculation", *[f"  {k:<26}{val}" for k, val in steps],
            "", f"RESULT        {res_text}"])
        row = dict(result=res_text, solved_for="sample size" if mode == "n" else "margin of error",
                   case=case, variable="Quantitative" if quant else "Two-valued",
                   population="Finite" if finite else "Large", confidence_pct=f"{conf * 100:g}", z=f"{z:.4f}",
                   spread_name=sp_name, spread_value=f"{spread:g}", margin_of_error_or_n=f"{input_value:g}",
                   population_size=N if finite else "", nonresponse_pct=f"{r * 100:g}", design_effect=f"{deff:g}")
        self.current = dict(
            result=result_value, line=line, row=row, report=report,
            state={k: v.get() for k, v in self.persist.items()},
            summary=(f"{summary_head} | {TITLES[case]} | confidence {conf * 100:g}% (z = {z:.4f}), {sp}, "
                     + (f"d = {vals['d']:g}" if mode == "n" else f"n = {frac_n:,}")
                     + (f", N = {N:,}" if finite else "") + adj_txt))

    # ---- sensitivity ----
    def update_sensitivity(self):
        c, px = self.c, self.px
        case, mode = self.case(), self.v_mode.get()
        quant, finite = case in ("1", "2"), case in ("2", "4")
        vals = self.vals
        for w in self.sens_table.winfo_children():
            w.destroy()
        self.chart.delete("all")
        self.sens_data = None

        needed = ["spread", "nr", "deff"] + (["N"] if finite else [])
        if any(k not in vals for k in needed):
            self.sens_msg.config(text="Complete the Calculator inputs to see this table.", fg=c["err"])
            return
        self.sens_msg.config(text="Total sample after adjustments, for each confidence level.", fg=c["dim"])

        spread, r, deff, N = vals["spread"], vals["nr"], vals["deff"], vals.get("N")
        d_cur = vals.get("d") if mode == "n" else None
        conf_cur = vals.get("conf")
        if quant:
            s = math.sqrt(spread) if case == "2" else spread
            base = [float(f"{s * k:.3g}") for k in (0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5)]
        else:
            base = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10]
        rows = sorted({round(x, 10) for x in base + ([d_cur] if d_cur else [])})
        rows = [x for x in rows if x > 0]
        confs = sorted({0.90, 0.95, 0.99} | ({round(conf_cur, 6)} if conf_cur else set()))
        grid = [[final_size(case, z_value(cf), spread, d, N, deff, r) for d in rows] for cf in confs]

        def fmt_d(d):
            return f"{d * 100:g}%" if not quant else f"{d:g}"

        hdr = dict(font=self.F["cap"], fg=c["dim"], bg=c["card"], anchor="e")
        tk.Label(self.sens_table, text="MARGIN (d)", **{**hdr, "anchor": "w"}).grid(row=0, column=0, sticky="w",
                                                                                      pady=(0, px(6)))
        for ci, cf in enumerate(confs):
            tk.Label(self.sens_table, text=f"{cf * 100:g}%", **hdr).grid(row=0, column=ci + 1, sticky="e",
                                                                         padx=(px(14), 0), pady=(0, px(6)))
        for ri, d in enumerate(rows):
            is_row = d_cur is not None and abs(d - d_cur) < 1e-12
            tk.Label(self.sens_table, text=fmt_d(d), font=self.F["mono_s"], fg=c["text"], bg=c["card"],
                     anchor="w").grid(row=ri + 1, column=0, sticky="w", pady=px(2))
            for ci, cf in enumerate(confs):
                here = is_row and conf_cur is not None and abs(cf - conf_cur) < 1e-6
                tk.Label(self.sens_table, text=f"{grid[ci][ri]:,}", anchor="e",
                         font=self.F["mono_s"] if not here else (self.F["mono_s"][0], 9, "bold"),
                         fg=c["accent"] if here and c is DARK else c["text"],
                         bg=c["soft"] if here else c["card"], padx=px(6)).grid(
                    row=ri + 1, column=ci + 1, sticky="e", padx=(px(14), 0), pady=px(2))

        self.sens_data = dict(rows=rows, confs=confs, grid=grid, quant=quant)
        self.draw_chart(rows, confs, grid, d_cur, conf_cur, fmt_d)

    def draw_chart(self, rows, confs, grid, d_cur, conf_cur, fmt_d):
        cv, c, F, px = self.chart, self.c, self.F, self.px
        W, H = int(cv["width"]), int(cv["height"])
        L, R, T, B = px(50), px(14), px(36), px(42)
        pw, ph = W - L - R, H - T - B
        if len(rows) < 2:
            return
        dmin, dmax = rows[0], rows[-1]
        nmax = max(max(col) for col in grid)

        def X(d):
            return L + (d - dmin) / (dmax - dmin) * pw

        def Y(n):
            return T + ph - n / nmax * ph

        for part in (0, 0.5, 1):
            y = T + ph - part * ph
            cv.create_line(L, y, L + pw, y, fill=c["border"])
            cv.create_text(L - px(6), y, text=short(nmax * part), anchor="e", fill=c["dim"], font=F["small"])
        for d in (rows[0], rows[len(rows) // 2], rows[-1]):
            cv.create_text(X(d), T + ph + px(8), text=fmt_d(d), anchor="n", fill=c["dim"], font=F["small"])
        cv.create_text(L + pw / 2, H - px(4), text="margin of error (d)", anchor="s", fill=c["dim"], font=F["small"])

        for ci, cf in enumerate(confs):
            col = c["lines"][ci % len(c["lines"])]
            pts = [(X(d), Y(grid[ci][ri])) for ri, d in enumerate(rows)]
            cv.create_line(*[v for p in pts for v in p], fill=col, width=2)
            for x, y in pts:
                cv.create_oval(x - 2, y - 2, x + 2, y + 2, fill=col, outline=col)
        x = L
        for ci, cf in enumerate(confs):
            col = c["lines"][ci % len(c["lines"])]
            cv.create_line(x, px(14), x + px(18), px(14), fill=col, width=2)
            cv.create_text(x + px(24), px(14), text=f"{cf * 100:g}%", anchor="w", fill=c["text"], font=F["small"])
            x += px(66)
        if d_cur is not None and conf_cur is not None:
            for ci, cf in enumerate(confs):
                if abs(cf - conf_cur) < 1e-6:
                    for ri, d in enumerate(rows):
                        if abs(d - d_cur) < 1e-12:
                            x, y = X(d), Y(grid[ci][ri])
                            cv.create_oval(x - 6, y - 6, x + 6, y + 6, outline=c["accent"], width=2)

    # ---- actions ----
    def copy(self):
        if not self.current:
            return
        self.clipboard_clear()
        self.clipboard_append(self.current["summary"])
        self.update()
        self.flash(self.btn_copy, "Copied  ✓")

    def save_history(self):
        if not self.current:
            return
        if not (self.history and self.history[0]["line"] == self.current["line"]):
            self.history.insert(0, dict(line=self.current["line"], state=self.current["state"],
                                        row=self.current["row"]))
            del self.history[MAX_HISTORY:]
            self.fill_history()
            self.save_config()
        self.flash(self.btn_save, "Saved  ✓")

    def apply_state(self, state):
        for k, var in self.persist.items():
            val = state.get(k)
            if isinstance(val, str) and len(val) < 40 and (k not in self.modes or val in self.modes[k]):
                var.set(val)

    def restore(self, _event=None):
        sel = self.hist.curselection()
        if not sel:
            return
        self.apply_state(self.history[sel[0]]["state"])
        self.on_mode()
        self.show_tab("calc")

    def delete_history(self):
        sel = self.hist.curselection()
        if sel:
            del self.history[sel[0]]
            self.fill_history()
            self.save_config()

    def clear_history(self):
        self.history.clear()
        self.fill_history()
        self.save_config()

    def reset(self):
        for k, var in self.persist.items():
            if k not in self.modes:
                var.set(self.defaults[k])

    def toggle_theme(self):
        self.c = DARK if self.c is LIGHT else LIGHT
        self.shell.destroy()
        self.build()
        self.save_config()

    # ---- export ----
    def ask_path(self, title, ext, types, name):
        return filedialog.asksaveasfilename(title=title, defaultextension=ext, filetypes=types, initialfile=name)

    def safe_write(self, fn, *args):
        try:
            fn(*args)
        except OSError as e:
            messagebox.showerror("Export failed", str(e))

    def export_report(self):
        if not self.current:
            return
        path = self.ask_path("Export report", ".txt", [("Text file", "*.txt")], "sample_size_report.txt")
        if path:
            self.safe_write(write_text, path, self.current["report"] + "\n")
            self.flash(self.btn_export, "Exported  ✓")

    def export_history(self):
        if not self.history:
            return
        path = self.ask_path("Export history", ".csv", [("CSV file", "*.csv")], "sample_size_history.csv")
        if path:
            self.safe_write(write_csv, path, CSV_FIELDS, [h["row"] for h in self.history])

    def export_sens(self):
        d = self.sens_data
        if not d:
            return
        path = self.ask_path("Export sensitivity table", ".csv", [("CSV file", "*.csv")], "sample_size_sensitivity.csv")
        if path:
            fields = ["margin_of_error"] + [f"n_at_{cf * 100:g}pct" for cf in d["confs"]]
            rows = [dict([("margin_of_error", f"{x * 100:g}%" if not d["quant"] else f"{x:g}")]
                         + [(fields[ci + 1], d["grid"][ci][ri]) for ci in range(len(d["confs"]))])
                    for ri, x in enumerate(d["rows"])]
            self.safe_write(write_csv, path, fields, rows)

    # ---- persistence ----
    def load_config(self):
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(data, dict):
            return
        if data.get("theme") == "dark":
            self.c = DARK
        if isinstance(data.get("inputs"), dict):
            self.apply_state(data["inputs"])
        for h in (data.get("history") or [])[:MAX_HISTORY]:
            if (isinstance(h, dict) and isinstance(h.get("line"), str) and isinstance(h.get("state"), dict)
                    and isinstance(h.get("row"), dict)):
                self.history.append(h)

    def save_config(self):
        data = dict(theme="dark" if self.c is DARK else "light",
                    inputs={k: v.get() for k, v in self.persist.items()}, history=self.history)
        try:
            CONFIG_PATH.write_text(json.dumps(data, indent=1), encoding="utf-8")
        except OSError:
            pass

    def on_close(self):
        self.save_config()
        self.destroy()


def main():
    try:  # sharper text on Windows
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    App().mainloop()


if __name__ == "__main__":
    main()
