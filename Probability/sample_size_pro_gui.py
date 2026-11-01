#!/usr/bin/env python3
"""
Sample Size Calculator - designed GUI (tkinter, standard library only)

Same maths as the simple version, with a full interface:
  - segmented selectors for variable type and population
  - live formula card, live result, step-by-step calculation
  - inline validation with hints under every field
  - light / dark theme switch, copy result, history (double-click to restore)
"""
import math
import tkinter as tk
from statistics import NormalDist
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

# ───────────────────────── themes ─────────────────────────
LIGHT = dict(bg="#f5f5f4", card="#ffffff", border="#e4e4e2", text="#171717", dim="#737373",
             accent="#171717", accent_fg="#ffffff", accent_hover="#000000", soft="#f0f0ee",
             chip="#f0f0ee", chip_hover="#e4e4e2", input_bg="#ffffff", input_off="#f5f5f4",
             sel="#e9e9e6", err="#dc2626", toggle="Dark")
DARK = dict(bg="#0b0d0e", card="#111416", border="#1f2528", text="#c9d1d3", dim="#6b777b",
            accent="#39ff88", accent_fg="#0b0d0e", accent_hover="#2fd673", soft="#143022",
            chip="#161b1d", chip_hover="#1f2528", input_bg="#0b0d0e", input_off="#0f1214",
            sel="#143022", err="#ff5c5c", toggle="Light")

# ───────────────────────── cases ─────────────────────────
CASES = {"1": ("quant", "large"), "2": ("quant", "finite"),
         "3": ("prop", "large"), "4": ("prop", "finite")}
CASE_OF = {v: k for k, v in CASES.items()}
TITLES = {"1": "Quantitative · Large population", "2": "Quantitative · Finite population",
          "3": "Two-valued · Large population", "4": "Two-valued · Finite population"}


def frac(num, den):
    """Draw 'n = num / den' as a three-line fraction."""
    w = max(len(num), len(den)) + 2
    return f"    {num.center(w)}\nn = {'─' * w}\n    {den.center(w)}"


FORMULAS = {
    "1": "\nn = (z · s / d)²",
    "2": frac("N · z² · s²", "d² · (N − 1) + z² · s²"),
    "3": frac("z² · p · q", "d²") + "     (q = 1 − p)",
    "4": frac("N · z² · p · q", "d² · (N − 1) + z² · p · q"),
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
    c = v / 100 if v > 1 else v          # "95" and "95%" and "0.95" all mean 95 %
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


def v_pop(text):
    v = num(text)
    if v < 2 or v != int(v):
        raise ValueError("Whole number, at least 2")
    return int(v)


# ───────────────────────── maths ─────────────────────────
def calculate(case, z, spread, d, N):
    if case == "1":
        v = spread ** 2              # spread = s
    elif case == "2":
        v = spread                   # spread = variance (s^2)
    else:
        v = spread * (1 - spread)    # spread = p, v = p * q

    if case in ("1", "3"):
        n = z ** 2 * v / d ** 2
    else:
        n = N * z ** 2 * v / (d ** 2 * (N - 1) + z ** 2 * v)
    return n, v


def describe(case, z, spread, v, d, N):
    zs = f"{z:.4f}"
    if case == "1":
        term = f"s² = {spread:g}² = {v:g}"
        sub = f"({zs} × {spread:g} / {d:g})²"
    elif case == "2":
        term = f"s² = {v:g}"
        sub = f"{N:,} × {zs}² × {v:g} / ({d:g}² × ({N:,} − 1) + {zs}² × {v:g})"
    elif case == "3":
        term = f"p·q = {spread:g} × {1 - spread:g} = {v:.4g}"
        sub = f"{zs}² × {v:.4g} / {d:g}²"
    else:
        term = f"p·q = {spread:g} × {1 - spread:g} = {v:.4g}"
        sub = f"{N:,} × {zs}² × {v:.4g} / ({d:g}² × ({N:,} − 1) + {zs}² × {v:.4g})"
    return term, sub


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
        self.history = []
        self.current = None
        self.focus_key = None

        fams = set(tkfont.families())
        ui = next((f for f in ("Segoe UI", "SF Pro Text", "Helvetica Neue", "Inter", "DejaVu Sans", "Arial")
                   if f in fams), "Helvetica")
        mono = next((f for f in ("Cascadia Mono", "Consolas", "JetBrains Mono", "Menlo", "DejaVu Sans Mono",
                                 "Courier New") if f in fams), "Courier")
        self.F = dict(base=(ui, 10), small=(ui, 9), bold=(ui, 10, "bold"), cap=(ui, 8, "bold"),
                      title=(ui, 19, "bold"), big=(ui, 42, "bold"), mono=(mono, 10), mono_s=(mono, 9),
                      mono_b=(mono, 11))

        self.v_type = tk.StringVar(value="quant")
        self.v_pop = tk.StringVar(value="large")
        self.v_conf = tk.StringVar(value="95")
        self.v_s = tk.StringVar(value="10")
        self.v_var = tk.StringVar(value="100")
        self.v_p = tk.StringVar(value="0.5")
        self.v_dq = tk.StringVar(value="1")
        self.v_dp = tk.StringVar(value="0.05")
        self.v_N = tk.StringVar(value="1000")
        self.inputs = [self.v_conf, self.v_s, self.v_var, self.v_p, self.v_dq, self.v_dp, self.v_N]
        self.defaults = [v.get() for v in self.inputs]

        self.scrolling = False
        self.build()
        for v in self.inputs:
            v.trace_add("write", self.refresh)
        self.bind("<Return>", lambda e: self.save_history())
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind_all(seq, self.on_wheel)

    # ---- helpers ----
    def px(self, v):
        return round(v * self.sc)

    def case(self):
        return CASE_OF[(self.v_type.get(), self.v_pop.get())]

    def spread_var(self):
        return {"1": self.v_s, "2": self.v_var, "3": self.v_p, "4": self.v_p}[self.case()]

    def d_var(self):
        return self.v_dq if self.case() in ("1", "2") else self.v_dp

    def card(self, parent, title):
        c, px = self.c, self.px
        outer = tk.Frame(parent, bg=c["border"])
        inner = tk.Frame(outer, bg=c["card"], padx=px(20), pady=px(18))
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Label(inner, text=title.upper(), font=self.F["cap"], fg=c["dim"], bg=c["card"],
                 anchor="w").pack(fill="x", pady=(0, px(10)))
        tk.Frame(inner, width=px(390), height=1, bg=c["card"]).pack()   # fixes column width
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
        button.config(text=text)
        self.after(900, lambda: button.winfo_exists() and button.config(text=button.base_text))

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
        self.root = tk.Frame(self.canvas, bg=c["bg"], padx=px(28), pady=px(22))
        self.canvas.create_window((0, 0), window=self.root, anchor="nw")
        self.fields = {}

        # header
        head = tk.Frame(self.root, bg=c["bg"])
        head.pack(fill="x", pady=(0, px(18)))
        titles = tk.Frame(head, bg=c["bg"])
        titles.pack(side="left")
        tk.Label(titles, text="Sample Size Calculator", font=F["title"], fg=c["text"], bg=c["bg"]).pack(anchor="w")
        tk.Label(titles, text="Means and proportions  ·  large or finite populations", font=F["base"],
                 fg=c["dim"], bg=c["bg"]).pack(anchor="w", pady=(2, 0))
        theme_btn = self.button(head, "◐  " + c["toggle"], self.toggle_theme)
        theme_btn.pack(side="right", anchor="n")

        body = tk.Frame(self.root, bg=c["bg"])
        body.pack()
        left = tk.Frame(body, bg=c["bg"])
        right = tk.Frame(body, bg=c["bg"])
        left.grid(row=0, column=0, sticky="n")
        right.grid(row=0, column=1, sticky="n", padx=(px(18), 0))

        self.build_design(left)
        self.build_parameters(left)
        self.build_result(right)
        self.build_history(right)

        tk.Label(self.root, text="Enter  save to history    ·    double-click a history row to restore it",
                 font=F["small"], fg=c["dim"], bg=c["bg"]).pack(anchor="w", pady=(px(14), 0))
        self.on_mode()
        self.fit_window()

    def fit_window(self):
        """Size the window to its content; add a scrollbar if the screen is too small."""
        self.update_idletasks()
        w, h = self.root.winfo_reqwidth(), self.root.winfo_reqheight()
        limit = self.winfo_screenheight() - self.px(120)
        self.scrolling = h > limit
        self.canvas.configure(width=w, height=min(h, limit), scrollregion=(0, 0, w, h))
        if self.scrolling:
            self.scrollbar.pack(side="right", fill="y")

    def on_wheel(self, event):
        if self.scrolling:
            up = event.num == 4 or getattr(event, "delta", 0) > 0
            self.canvas.yview_scroll(-2 if up else 2, "units")

    def build_design(self, parent):
        c, F, px = self.c, self.F, self.px
        outer, inner = self.card(parent, "Study design")
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

    def build_parameters(self, parent):
        c, F, px = self.c, self.F, self.px
        outer, inner = self.card(parent, "Parameters")
        outer.pack(fill="x", pady=(px(16), 0))
        form = tk.Frame(inner, bg=c["card"])
        form.pack(fill="x")
        form.columnconfigure(0, weight=1)

        for i, key in enumerate(("conf", "spread", "d", "N")):
            r = i * 3
            lab = tk.Label(form, font=F["bold"], fg=c["text"], bg=c["card"], anchor="w")
            lab.grid(row=r, column=0, sticky="w", pady=(px(9) if i else 0, px(4)))
            chips = tk.Frame(form, bg=c["card"])
            chips.grid(row=r, column=1, sticky="e", pady=(px(9) if i else 0, px(4)))

            wrap = tk.Frame(form, bg=c["border"], padx=1, pady=1)
            wrap.grid(row=r + 1, column=0, columnspan=2, sticky="ew")
            box = tk.Frame(wrap, bg=c["input_bg"], padx=px(9), pady=px(5))
            box.pack(fill="x")
            ent = tk.Entry(box, font=F["base"], relief="flat", bd=0, bg=c["input_bg"], fg=c["text"],
                           insertbackground=c["accent"], disabledbackground=c["input_off"],
                           disabledforeground=c["dim"], highlightthickness=0)
            ent.pack(fill="x")
            ent.bind("<FocusIn>", lambda e, k=key: self.set_focus(k))
            ent.bind("<FocusOut>", lambda e: self.set_focus(None))

            msg = tk.Label(form, font=F["small"], fg=c["dim"], bg=c["card"], anchor="w", justify="left",
                           wraplength=px(370))
            msg.grid(row=r + 2, column=0, columnspan=2, sticky="w", pady=(px(3), 0))
            self.fields[key] = dict(lab=lab, ent=ent, box=box, wrap=wrap, msg=msg, chips=chips, error=False)

        # fixed-variable fields and chips
        self.fields["conf"]["ent"].config(textvariable=self.v_conf)
        self.fields["N"]["ent"].config(textvariable=self.v_N)
        for t in ("90", "95", "99"):
            self.chip(self.fields["conf"]["chips"], t + "%", lambda t=t: self.v_conf.set(t)).pack(
                side="left", padx=(px(4), 0))
        self.chip_p = self.chip(self.fields["spread"]["chips"], "p = 0.5", lambda: self.v_p.set("0.5"))

    def build_result(self, parent):
        c, F, px = self.c, self.F, self.px
        outer, inner = self.card(parent, "Required sample size")
        outer.pack(fill="x")
        self.l_n = tk.Label(inner, text="—", font=F["big"], fg=c["accent"], bg=c["card"], anchor="w")
        self.l_n.pack(fill="x")
        self.l_sub = tk.Label(inner, font=F["base"], fg=c["dim"], bg=c["card"], anchor="w", justify="left",
                              wraplength=px(390))
        self.l_sub.pack(fill="x", pady=(0, px(12)))
        tk.Frame(inner, bg=c["border"], height=1).pack(fill="x", pady=(0, px(10)))

        grid = tk.Frame(inner, bg=c["card"])
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)
        self.steps = {}
        for i, key in enumerate(("z", "Variance term", "Substitution", "n (unrounded)", "n (rounded up)", "n / N")):
            tk.Label(grid, text=key, font=F["small"], fg=c["dim"], bg=c["card"], anchor="nw",
                     width=14).grid(row=i, column=0, sticky="nw", pady=px(3))
            v = tk.Label(grid, text="—", font=F["mono_s"], fg=c["text"], bg=c["card"], anchor="nw",
                         justify="left", wraplength=px(260), height=3 if key == "Substitution" else 1)
            v.grid(row=i, column=1, sticky="nw", pady=px(3))
            self.steps[key] = v

        self.l_notes = tk.Label(inner, font=F["small"], fg=c["dim"], bg=c["card"], anchor="nw",
                                justify="left", wraplength=px(390), height=2)
        self.l_notes.pack(fill="x", pady=(px(8), px(12)))

        row = tk.Frame(inner, bg=c["card"])
        row.pack(fill="x")
        self.btn_copy = self.button(row, "Copy result", self.copy, primary=True)
        self.btn_copy.pack(side="left")
        self.btn_save = self.button(row, "Save to history", self.save_history)
        self.btn_save.pack(side="left", padx=(px(8), 0))
        self.button(row, "Reset", self.reset).pack(side="right")

    def build_history(self, parent):
        c, F, px = self.c, self.F, self.px
        outer, inner = self.card(parent, "History")
        outer.pack(fill="x", pady=(px(16), 0))
        self.hist = tk.Listbox(inner, font=F["mono_s"], height=4, relief="flat", bd=0, bg=c["input_bg"],
                               fg=c["text"], highlightthickness=1, highlightbackground=c["border"],
                               highlightcolor=c["border"], selectbackground=c["sel"],
                               selectforeground=c["text"], activestyle="none", exportselection=False)
        self.hist.pack(fill="x")
        self.hist.bind("<Double-Button-1>", self.restore)
        for h in self.history:
            self.hist.insert("end", h["line"])
        link = tk.Label(inner, text="Clear history", font=F["small"], fg=c["dim"], bg=c["card"], cursor="hand2")
        link.pack(anchor="e", pady=(px(8), 0))
        link.bind("<Button-1>", lambda e: self.clear_history())
        link.bind("<Enter>", lambda e: link.config(fg=c["text"]))
        link.bind("<Leave>", lambda e: link.config(fg=c["dim"]))

    # ---- state changes ----
    def on_mode(self):
        c, px = self.c, self.px
        case = self.case()
        quant = case in ("1", "2")
        finite = case in ("2", "4")
        f = self.fields

        self.seg_type.render()
        self.seg_pop.render()
        self.l_case.config(text=f"CASE {case}  ·  {TITLES[case].upper()}")
        self.l_formula.config(text=FORMULAS[case])

        f["conf"]["lab"].config(text="Confidence level (%)")
        f["spread"]["lab"].config(text={"1": "Standard deviation (s)", "2": "Variance (s²)",
                                        "3": "Proportion (p)", "4": "Proportion (p)"}[case])
        f["d"]["lab"].config(text="Margin of error (d)")
        f["N"]["lab"].config(text="Population size (N)", fg=c["text"] if finite else c["dim"])
        f["spread"]["ent"].config(textvariable=self.spread_var())
        f["d"]["ent"].config(textvariable=self.d_var())
        f["N"]["ent"].config(state="normal" if finite else "disabled")
        f["N"]["box"].config(bg=c["input_bg"] if finite else c["input_off"])

        if quant:
            self.chip_p.pack_forget()
        else:
            self.chip_p.pack(side="left", padx=(px(4), 0))

        self.hints = {
            "conf": "Typical: 90, 95 or 99   ·   also accepts 0.95 or 95%",
            "spread": {"1": "Population standard deviation (pilot study or literature)",
                       "2": "Enter the variance (s²), not the standard deviation",
                       "3": "Expected proportion   ·   0.5 if unknown (gives the largest n)",
                       "4": "Expected proportion   ·   0.5 if unknown (gives the largest n)"}[case],
            "d": ("Absolute error, in the same unit as the variable" if quant
                  else "Absolute error   ·   0.05 or 5% means ±5 percentage points"),
            "N": ("Total number of units in the population" if finite else "Not used for a large population"),
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
        for lab in self.steps.values():
            lab.config(text="—")
        self.l_notes.config(text="")

    def refresh(self, *_):
        case = self.case()
        quant = case in ("1", "2")
        finite = case in ("2", "4")

        checks = [("conf", self.v_conf, v_conf),
                  ("spread", self.spread_var(), v_positive if quant else v_fraction),
                  ("d", self.d_var(), v_positive if quant else v_fraction)]
        if finite:
            checks.append(("N", self.v_N, v_pop))

        vals, ok = {}, True
        for key, var, check in checks:
            try:
                vals[key] = check(var.get())
                self.set_msg(key, self.hints[key], False)
            except ValueError as e:
                ok = False
                self.set_msg(key, str(e), True)
        if not finite:
            self.set_msg("N", self.hints["N"], False)
        if not ok:
            self.set_empty()
            return

        conf, spread, d, N = vals["conf"], vals["spread"], vals["d"], vals.get("N")
        z = NormalDist().inv_cdf(1 - (1 - conf) / 2)
        n_raw, v = calculate(case, z, spread, d, N)
        n = math.ceil(round(n_raw, 9))
        term, sub = describe(case, z, spread, v, d, N)

        self.l_n.config(text=f"{n:,}", fg=self.c["accent"])
        self.l_sub.config(text="units needed in the sample (always rounded up)")
        self.steps["z"].config(text=f"{z:.4f}   ({conf * 100:g}% confidence)")
        self.steps["Variance term"].config(text=term)
        self.steps["Substitution"].config(text=sub)
        self.steps["n (unrounded)"].config(text=f"{n_raw:,.2f}")
        self.steps["n (rounded up)"].config(text=f"{n:,}")
        self.steps["n / N"].config(text=f"{n / N:.1%}" if finite else "—")

        if finite and n >= N:
            note = "n reaches N: survey the whole population (census)."
        elif finite and (z * z * v / (d * d)) / N < 0.05:
            note = "Finite-population correction is negligible here (n₀ / N < 5%)."
        elif not finite:
            note = "If n would exceed 5% of N, switch to a finite population."
        else:
            note = ""
        self.l_notes.config(text=note)

        sp = {"1": f"s = {spread:g}", "2": f"s² = {spread:g}", "3": f"p = {spread:g}", "4": f"p = {spread:g}"}[case]
        self.current = dict(
            n=n,
            summary=(f"Sample size n = {n:,} | {TITLES[case]} | confidence {conf * 100:g}% (z = {z:.4f}), "
                     f"{sp}, d = {d:g}" + (f", N = {N:,}" if finite else "")),
            line=(f"{n:>7,}  C{case}  {conf * 100:g}%  {sp}  d={d:g}" + (f"  N={N:,}" if finite else "")),
            state=dict(case=case, conf=self.v_conf.get(), spread=self.spread_var().get(),
                       d=self.d_var().get(), N=self.v_N.get()),
        )

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
            self.history.insert(0, dict(line=self.current["line"], state=self.current["state"]))
            del self.history[12:]
            self.hist.delete(0, "end")
            for h in self.history:
                self.hist.insert("end", h["line"])
        self.flash(self.btn_save, "Saved  ✓")

    def restore(self, _event=None):
        sel = self.hist.curselection()
        if not sel:
            return
        st = self.history[sel[0]]["state"]
        self.v_type.set(CASES[st["case"]][0])
        self.v_pop.set(CASES[st["case"]][1])
        self.v_conf.set(st["conf"])
        self.v_N.set(st["N"])
        {"1": self.v_s, "2": self.v_var, "3": self.v_p, "4": self.v_p}[st["case"]].set(st["spread"])
        (self.v_dq if st["case"] in ("1", "2") else self.v_dp).set(st["d"])
        self.on_mode()

    def clear_history(self):
        self.history.clear()
        self.hist.delete(0, "end")

    def reset(self):
        for var, default in zip(self.inputs, self.defaults):
            var.set(default)

    def toggle_theme(self):
        self.c = DARK if self.c is LIGHT else LIGHT
        self.shell.destroy()
        self.build()


def main():
    try:  # sharper text on Windows
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    App().mainloop()


if __name__ == "__main__":
    main()
