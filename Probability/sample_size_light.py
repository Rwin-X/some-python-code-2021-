#!/usr/bin/env python3
"""
Sample Size Calculator - simple white version (tkinter, standard library only)

Quantitative variable   large: n = (z*sigma / d)^2
                        finite: n = N*z^2*sigma^2 / (d^2*(N-1) + z^2*sigma^2)
Two-valued variable     large: n = z^2*p*(1-p) / d^2
                        finite: n = N*z^2*p*(1-p) / (d^2*(N-1) + z^2*p*(1-p))
"""
import math
import tkinter as tk
from statistics import NormalDist

FORMULAS = {
    ("quant", False): "n = (z·σ / d)²",
    ("quant", True): "n = N·z²·σ² / (d²·(N−1) + z²·σ²)",
    ("prop", False): "n = z²·p·(1−p) / d²",
    ("prop", True): "n = N·z²·p·(1−p) / (d²·(N−1) + z²·p·(1−p))",
}


def num(text, name, pct=False):
    t = text.strip().replace(",", "")
    if not t:
        raise ValueError(f"{name}: value required")
    is_pct = t.endswith("%")
    if is_pct:
        if not pct:
            raise ValueError(f"{name}: '%' not allowed")
        t = t[:-1]
    try:
        v = float(t)
    except ValueError:
        raise ValueError(f"{name}: not a number") from None
    if not math.isfinite(v):
        raise ValueError(f"{name}: invalid number")
    return v / 100 if is_pct else v


def fraction(text, name):
    v = num(text, name, pct=True)
    if not 0 < v < 1:
        raise ValueError(f"{name} must be between 0 and 1 (or e.g. 5%)")
    return v


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sample Size")
        self.configure(bg="white", padx=28, pady=24)
        self.resizable(False, False)
        font = ("Segoe UI", 11)
        self.font = font

        self.kind = tk.StringVar(value="quant")
        self.pop = tk.StringVar(value="large")
        self.vars = {k: tk.StringVar(value=v) for k, v in
                     dict(conf="95", sigma="10", p="0.5", dq="1", dp="0.05", N="1000").items()}

        self._radios("Variable", self.kind, [("Quantitative", "quant"), ("Two-valued", "prop")])
        self._radios("Population", self.pop, [("Large", "large"), ("Finite", "finite")])

        form = tk.Frame(self, bg="white")
        form.pack(fill="x", pady=(8, 0))
        self.rows = {}
        for i, (key, label) in enumerate([("conf", "Confidence level (%)"),
                                          ("sigma", "Std. deviation (σ)"),
                                          ("p", "Proportion (p)"),
                                          ("dq", "Margin of error (d)"),
                                          ("dp", "Margin of error (d)"),
                                          ("N", "Population size (N)")]):
            lab = tk.Label(form, text=label, font=font, bg="white", anchor="w")
            ent = tk.Entry(form, textvariable=self.vars[key], font=font, width=12, relief="solid", bd=1,
                           highlightthickness=0, disabledbackground="#f0f0f0")
            row = {"conf": 0, "sigma": 1, "p": 1, "dq": 2, "dp": 2, "N": 3}[key]
            lab.grid(row=row, column=0, sticky="w", pady=5, padx=(0, 18))
            ent.grid(row=row, column=1, sticky="w", pady=5, ipady=3)
            self.rows[key] = (lab, ent)

        tk.Frame(self, bg="#dddddd", height=1).pack(fill="x", pady=18)

        self.result = tk.Label(self, text="", font=("Segoe UI", 30, "bold"), bg="white", anchor="w")
        self.result.pack(anchor="w")
        self.info = tk.Label(self, text="", font=("Segoe UI", 10), fg="#666666", bg="white",
                             anchor="w", justify="left", wraplength=380)
        self.info.pack(anchor="w", pady=(2, 0))

        self.sync()
        for v in self.vars.values():
            v.trace_add("write", self.calc)

    def _radios(self, title, var, items):
        fr = tk.Frame(self, bg="white")
        fr.pack(anchor="w", pady=3)
        tk.Label(fr, text=title, font=self.font, bg="white", width=11, anchor="w").pack(side="left")
        for text, val in items:
            tk.Radiobutton(fr, text=text, value=val, variable=var, command=self.sync, font=self.font,
                           bg="white", activebackground="white", highlightthickness=0).pack(side="left", padx=6)

    def sync(self):
        quant = self.kind.get() == "quant"
        for key, show in (("sigma", quant), ("dq", quant), ("p", not quant), ("dp", not quant)):
            for w in self.rows[key]:
                w.grid() if show else w.grid_remove()
        finite = self.pop.get() == "finite"
        lab, ent = self.rows["N"]
        ent.config(state="normal" if finite else "disabled")
        lab.config(fg="black" if finite else "#aaaaaa")
        self.calc()

    def calc(self, *_):
        try:
            quant = self.kind.get() == "quant"
            finite = self.pop.get() == "finite"
            v = {k: s.get() for k, s in self.vars.items()}

            conf = num(v["conf"], "Confidence", pct=True)
            conf = conf / 100 if conf > 1 else conf
            if not 0 < conf < 1:
                raise ValueError("Confidence must be between 0 and 100")

            if quant:
                s = num(v["sigma"], "σ")
                d = num(v["dq"], "d")
                if s <= 0 or d <= 0:
                    raise ValueError("σ and d must be greater than 0")
                var = s * s
            else:
                p = fraction(v["p"], "p")
                d = fraction(v["dp"], "d")
                var = p * (1 - p)

            z = NormalDist().inv_cdf(1 - (1 - conf) / 2)
            if finite:
                N = num(v["N"], "N")
                if N < 2 or N != int(N):
                    raise ValueError("N must be a whole number ≥ 2")
                n = N * z * z * var / (d * d * (N - 1) + z * z * var)
            else:
                n = z * z * var / (d * d)
            n = math.ceil(round(n, 9))
        except ValueError as e:
            self.result.config(text="—", fg="#aaaaaa")
            self.info.config(text=str(e), fg="#cc3333")
            return

        self.result.config(text=f"n = {n:,}", fg="black")
        self.info.config(text=f"z = {z:.4f}\n{FORMULAS[('quant' if quant else 'prop', finite)]}", fg="#666666")


if __name__ == "__main__":
    try:  # sharper text on Windows
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    App().mainloop()
