#!/usr/bin/env python3
"""
SAMPLE SIZE - minimal sample-size estimator (tkinter, standard library only)

Cases
  Quantitative variable
    large population    n = (z*sigma / d)^2
    finite population   n = N*z^2*sigma^2 / (d^2*(N-1) + z^2*sigma^2)
  Two-valued (dichotomous) variable
    large population    n = z^2*p*(1-p) / d^2
    finite population   n = N*z^2*p*(1-p) / (d^2*(N-1) + z^2*p*(1-p))

Extras: live results, "95" / "95%" / "0.95" accepted for confidence,
"5%" accepted for proportions, optional non-response adjustment.
"""
from __future__ import annotations

import math
import tkinter as tk
from statistics import NormalDist
from tkinter import font as tkfont
from tkinter import ttk

# ───────────────────────── palette ─────────────────────────
BG = "#0b0d0e"
PANEL = "#111416"
LINE = "#1f2528"
FG = "#c9d1d3"
DIM = "#6b777b"
ACC = "#39ff88"
SEL = "#143022"
ERR = "#ff5c5c"

MONO_PREF = ("JetBrains Mono", "Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Menlo", "Courier New")

FORMULAS = {
    ("quant", False): "n = (z·σ / d)²",
    ("quant", True): "n = N·z²·σ² / (d²·(N−1) + z²·σ²)",
    ("prop", False): "n = z²·p·(1−p) / d²",
    ("prop", True): "n = N·z²·p·(1−p) / (d²·(N−1) + z²·p·(1−p))",
}


# ───────────────────── core math (pure) ─────────────────────
def z_value(conf: float) -> float:
    """Two-sided critical value for a confidence level in (0, 1)."""
    return NormalDist().inv_cdf(1 - (1 - conf) / 2)


def _ceil(x: float) -> int:
    return math.ceil(round(x, 9))  # round() guards against float noise like 385.00000000001


def estimate(kind: str, finite: bool, conf: float, spread: float, d: float,
             N: int | None = None, nonresp: float = 0.0) -> dict:
    """
    kind    : "quant" (spread = sigma) or "prop" (spread = p)
    finite  : apply finite-population formula (needs N)
    conf    : confidence level, 0 < conf < 1
    d       : absolute margin of error
    nonresp : expected non-response rate, 0 <= r < 1
    """
    z = z_value(conf)
    var = spread ** 2 if kind == "quant" else spread * (1 - spread)
    n0 = z * z * var / (d * d)
    n_raw = N * z * z * var / (d * d * (N - 1) + z * z * var) if finite else n0
    n = _ceil(n_raw)
    n_adj = _ceil(n / (1 - nonresp)) if nonresp > 0 else n
    return {"z": z, "var": var, "n0": n0, "n_raw": n_raw, "n": n, "n_adj": n_adj}


# ───────────────────────── parsing ─────────────────────────
def num(text: str, name: str, pct: bool = False) -> float:
    t = text.strip().replace(",", "")
    if not t:
        raise ValueError(f"{name}: value required")
    is_pct = t.endswith("%")
    if is_pct:
        if not pct:
            raise ValueError(f"{name}: '%' not allowed here")
        t = t[:-1].strip()
    try:
        v = float(t)
    except ValueError:
        raise ValueError(f"{name}: '{text.strip()}' is not a number") from None
    if not math.isfinite(v):
        raise ValueError(f"{name}: invalid number")
    return v / 100 if is_pct else v


def parse_conf(text: str) -> float:
    v = num(text, "Confidence", pct=True)
    c = v / 100 if v > 1 else v  # "95" -> 0.95, "95%" and "0.95" already fractions
    if not 0 < c < 1:
        raise ValueError("Confidence must be between 0% and 100% (exclusive)")
    return c


def parse_fraction(text: str, name: str) -> float:
    v = num(text, name, pct=True)
    if not 0 < v < 1:
        raise ValueError(f"{name} must be between 0 and 1 (or write it as e.g. 5%)")
    return v


def parse_nonresp(text: str) -> float:
    raw = text.strip()
    if not raw:
        return 0.0
    v = num(raw, "Non-response", pct=True)
    if not raw.endswith("%"):
        v /= 100  # bare numbers are percentages in this field
    if not 0 <= v < 1:
        raise ValueError("Non-response must be between 0% and 100% (exclusive)")
    return v


# ─────────────────────────── GUI ───────────────────────────
class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SAMPLE SIZE")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.summary = ""

        fams = set(tkfont.families())
        mono = next((f for f in MONO_PREF if f in fams), "Courier")
        self.f = (mono, 10)
        self.f_s = (mono, 9)
        self.f_b = (mono, 10, "bold")
        self.f_h = (mono, 13, "bold")
        self.f_big = (mono, 44, "bold")

        self.v_type = tk.StringVar(value="quant")
        self.v_pop = tk.StringVar(value="large")
        self.v_conf = tk.StringVar(value="95")
        self.v_sigma = tk.StringVar(value="10")
        self.v_p = tk.StringVar(value="0.5")
        self.v_dq = tk.StringVar(value="1")
        self.v_dp = tk.StringVar(value="0.05")
        self.v_N = tk.StringVar(value="1000")
        self.v_nr = tk.StringVar(value="0")

        self._style()
        self._build()
        self._sync()
        for v in (self.v_conf, self.v_sigma, self.v_p, self.v_dq, self.v_dp, self.v_N, self.v_nr):
            v.trace_add("write", self.calc)
        self.calc()

    # ---- styling ----
    def _style(self) -> None:
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure("T.TEntry", fieldbackground=PANEL, foreground=FG, insertcolor=ACC,
                     bordercolor=LINE, lightcolor=LINE, darkcolor=LINE, padding=(6, 5))
        st.map("T.TEntry",
               bordercolor=[("focus", ACC)], lightcolor=[("focus", ACC)], darkcolor=[("focus", ACC)],
               fieldbackground=[("disabled", BG)], foreground=[("disabled", DIM)])
        st.configure("Seg.Toolbutton", background=PANEL, foreground=DIM, bordercolor=LINE,
                     lightcolor=PANEL, darkcolor=PANEL, focuscolor=PANEL, borderwidth=1,
                     relief="flat", padding=(16, 8), font=self.f)
        st.map("Seg.Toolbutton",
               background=[("selected", SEL), ("active", LINE)],
               foreground=[("selected", ACC), ("active", FG)],
               lightcolor=[("selected", SEL)], darkcolor=[("selected", SEL)])
        st.configure("Chip.TButton", background=PANEL, foreground=DIM, bordercolor=LINE,
                     lightcolor=PANEL, darkcolor=PANEL, focuscolor=PANEL, padding=(8, 3), font=self.f_s)
        st.map("Chip.TButton", background=[("active", LINE)], foreground=[("active", ACC)])
        st.configure("Act.TButton", background=PANEL, foreground=ACC, bordercolor=ACC,
                     lightcolor=PANEL, darkcolor=PANEL, focuscolor=PANEL, padding=(14, 7), font=self.f_b)
        st.map("Act.TButton", background=[("active", SEL)])

    # ---- layout ----
    def _rule(self, parent: tk.Misc) -> None:
        tk.Frame(parent, bg=LINE, height=1).pack(fill="x", pady=14)

    def _caption(self, parent: tk.Misc, text: str) -> None:
        tk.Label(parent, text=text, font=self.f_s, fg=DIM, bg=BG, anchor="w").pack(fill="x", pady=(0, 5))

    def _seg(self, parent: tk.Misc, var: tk.StringVar, items: list[tuple[str, str]]) -> None:
        fr = tk.Frame(parent, bg=BG)
        fr.pack(anchor="w", pady=(0, 12))
        for text, val in items:
            ttk.Radiobutton(fr, text=text, value=val, variable=var, style="Seg.Toolbutton",
                            command=self._sync, takefocus=False).pack(side="left", padx=(0, 4))

    def _field(self, parent: tk.Misc, row: int, label: str, var: tk.StringVar, hint: str):
        lab = tk.Label(parent, text=label, font=self.f, fg=FG, bg=BG, anchor="w")
        ent = ttk.Entry(parent, textvariable=var, style="T.TEntry", width=14, font=self.f)
        hnt = tk.Label(parent, text=hint, font=self.f_s, fg=DIM, bg=BG, anchor="w")
        lab.grid(row=row, column=0, sticky="w", pady=5, padx=(0, 16))
        ent.grid(row=row, column=1, sticky="w", pady=5)
        hnt.grid(row=row, column=2, sticky="w", padx=(12, 0))
        return lab, ent, hnt

    def _build(self) -> None:
        root = tk.Frame(self, bg=BG, padx=26, pady=22)
        root.pack(fill="both", expand=True)

        head = tk.Frame(root, bg=BG)
        head.pack(fill="x")
        tk.Label(head, text="SAMPLE SIZE", font=self.f_h, fg=ACC, bg=BG).pack(side="left")
        tk.Label(head, text="  estimator", font=self.f, fg=DIM, bg=BG).pack(side="left", pady=(2, 0))
        self._rule(root)

        self._caption(root, "VARIABLE")
        self._seg(root, self.v_type, [("Quantitative", "quant"), ("Two-valued", "prop")])
        self._caption(root, "POPULATION")
        self._seg(root, self.v_pop, [("Large", "large"), ("Finite", "finite")])
        self._rule(root)

        form = tk.Frame(root, bg=BG)
        form.pack(fill="x")

        # row 0 - confidence (+ chips)
        self._field(form, 0, "Confidence level", self.v_conf, "")
        chips = tk.Frame(form, bg=BG)
        chips.grid(row=0, column=2, sticky="w", padx=(12, 0))
        for c in ("90", "95", "99"):
            ttk.Button(chips, text=c + "%", style="Chip.TButton", takefocus=False,
                       command=lambda c=c: self.v_conf.set(c)).pack(side="left", padx=(0, 4))

        # row 1 - sigma | p       row 2 - d (per variable type)
        self.g_quant = [*self._field(form, 1, "Std. deviation  σ", self.v_sigma, "population SD (pilot / literature)"),
                        *self._field(form, 2, "Margin of error  d", self.v_dq, "absolute · same units as σ")]
        self.g_prop = [*self._field(form, 1, "Expected proportion  p", self.v_p, "0.5 → most conservative"),
                       *self._field(form, 2, "Margin of error  d", self.v_dp, "absolute · e.g. 0.05 or 5%")]

        # row 3 - N (always shown, disabled for large populations)
        self.lab_N, self.ent_N, self.hint_N = self._field(form, 3, "Population size  N", self.v_N, "finite population only")

        # row 4 - non-response
        self._field(form, 4, "Non-response  %", self.v_nr, "optional · inflates n")

        # result panel
        panel = tk.Frame(root, bg=PANEL, padx=20, pady=16, highlightthickness=1, highlightbackground=LINE)
        panel.pack(fill="x", pady=(18, 0))
        self.l_n = tk.Label(panel, text="—", font=self.f_big, fg=ACC, bg=PANEL, anchor="w")
        self.l_n.pack(anchor="w")
        self.l_sub = tk.Label(panel, text="", font=self.f, fg=DIM, bg=PANEL, anchor="w",
                              justify="left", wraplength=500)
        self.l_sub.pack(anchor="w", pady=(0, 10))
        tk.Frame(panel, bg=LINE, height=1).pack(fill="x", pady=(0, 10))
        self.l_det = tk.Label(panel, text="", font=self.f_s, fg=FG, bg=PANEL, anchor="nw",
                              justify="left", width=62, height=11)
        self.l_det.pack(anchor="w")

        self.btn = ttk.Button(root, text="COPY RESULT", style="Act.TButton", command=self.copy, takefocus=False)
        self.btn.pack(anchor="e", pady=(14, 0))

    # ---- mode switching ----
    def _sync(self) -> None:
        quant = self.v_type.get() == "quant"
        finite = self.v_pop.get() == "finite"
        for w in self.g_quant:
            w.grid() if quant else w.grid_remove()
        for w in self.g_prop:
            w.grid_remove() if quant else w.grid()
        self.ent_N.configure(state="normal" if finite else "disabled")
        self.lab_N.configure(fg=FG if finite else DIM)
        self.calc()

    # ---- calculation ----
    def _compute(self):
        quant = self.v_type.get() == "quant"
        finite = self.v_pop.get() == "finite"
        kind = "quant" if quant else "prop"

        conf = parse_conf(self.v_conf.get())
        if quant:
            spread = num(self.v_sigma.get(), "σ")
            if spread <= 0:
                raise ValueError("σ must be greater than 0")
            d = num(self.v_dq.get(), "d")
            if d <= 0:
                raise ValueError("d must be greater than 0")
            spread_txt = f"σ = {spread:g}"
        else:
            spread = parse_fraction(self.v_p.get(), "p")
            d = parse_fraction(self.v_dp.get(), "d")
            spread_txt = f"p = {spread:g}"

        N = None
        if finite:
            Nf = num(self.v_N.get(), "N")
            if Nf < 2 or Nf != int(Nf):
                raise ValueError("N must be a whole number ≥ 2")
            N = int(Nf)

        r = parse_nonresp(self.v_nr.get())
        res = estimate(kind, finite, conf, spread, d, N, r)
        z, n, n_adj = res["z"], res["n"], res["n_adj"]
        final = n_adj

        def kv(k: str, v: str) -> str:
            return f"{k:<19}{v}"

        lines = [
            kv("confidence", f"{conf * 100:g}%   (z = {z:.4f})"),
            kv("formula", FORMULAS[(kind, finite)]),
        ]
        if finite:
            lines.append(kv("n₀ (large pop.)", f"{res['n0']:,.2f}"))
        lines.append(kv("n (unrounded)", f"{res['n_raw']:,.2f}"))
        lines.append(kv("n (rounded up)", f"{n:,}"))
        if finite:
            lines.append(kv("sampling fraction", f"{n / N:.2%}  of N"))
        if r > 0:
            lines.append(kv("non-response", f"{r * 100:g}%  →  {n_adj:,}"))

        notes = []
        if finite and res["n0"] / N < 0.05:
            notes.append("note: finite correction is negligible (n₀/N < 5%).")
        if finite and final >= N:
            notes.append("note: n reaches N → survey the whole population (census).")
        if not finite:
            notes.append("note: if n would exceed 5% of N, switch to Finite.")
        if notes:
            lines.append("")
            lines.extend(notes)

        sub = "required sample size"
        if r > 0:
            sub += f"  ·  {n:,} before non-response adj."

        pop_txt = f"finite population (N = {N:,})" if finite else "large population"
        var_txt = "Quantitative variable" if quant else "Two-valued variable"
        summary = (f"Sample size n = {final:,} | {var_txt}, {pop_txt} | "
                   f"confidence {conf * 100:g}% (z = {z:.4f}), {spread_txt}, d = {d:g}"
                   + (f", non-response {r * 100:g}% (n = {n:,} before adj.)" if r > 0 else ""))
        return final, sub, "\n".join(lines), summary

    def calc(self, *_: object) -> None:
        try:
            final, sub, det, summary = self._compute()
        except ValueError as e:
            self.summary = ""
            self.l_n.config(text="—", fg=DIM)
            self.l_sub.config(text=str(e), fg=ERR)
            self.l_det.config(text="")
            return
        self.summary = summary
        self.l_n.config(text=f"{final:,}", fg=ACC)
        self.l_sub.config(text=sub, fg=DIM)
        self.l_det.config(text=det)

    def copy(self) -> None:
        if not self.summary:
            return
        self.clipboard_clear()
        self.clipboard_append(self.summary)
        self.update()
        self.btn.config(text="COPIED")
        self.after(900, lambda: self.btn.config(text="COPY RESULT"))


def main() -> None:
    try:  # crisp text on Windows high-DPI displays
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    App().mainloop()


if __name__ == "__main__":
    main()
