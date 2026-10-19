import math
import tkinter as tk
from tkinter import font as tkfont

from scipy import stats

# ---------- THEME (dark / phosphor green + cyan) ----------
BG = "#0b0f0c"
PANEL = "#111813"
BORDER = "#1f2b22"
FG = "#c9d6cc"
DIM = "#6b7d70"
GREEN = "#39ff88"
CYAN = "#3fd8ff"
RED = "#ff5c6c"


def pick_font(size=11, bold=False):
    """Prefer JetBrains Mono, fall back to other monospace fonts."""
    available = set(tkfont.families())
    for name in ("JetBrains Mono", "Consolas", "Menlo", "DejaVu Sans Mono", "Courier New"):
        if name in available:
            return (name, size, "bold" if bold else "normal")
    return ("TkFixedFont", size, "bold" if bold else "normal")


# ---------- CORE LOGIC (same as the original script) ----------
def parse_confidence(text):
    """Accepts 0.99, 99 or 99% and returns a value between 0 and 1."""
    text = text.strip().replace("%", "")
    value = float(text)
    if value > 1:
        value /= 100
    return value


def compute_ci(n, mean, std, conf):
    df = n - 1                                   # DARAGE AZADI
    alpha = 1 - conf
    t_critical = stats.t.ppf(1 - alpha / 2, df)  # t table value
    standard_error = std / math.sqrt(n)
    margin_error = t_critical * standard_error
    lower = mean - margin_error                  # KAMTARIN
    upper = mean + margin_error                  # BISHTARIN
    return {
        "n": n,
        "mean": mean,
        "std": std,
        "conf": conf,
        "df": df,
        "t": t_critical,
        "se": standard_error,
        "me": margin_error,
        "lower": lower,
        "upper": upper,
    }


# ---------- GUI ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("t Confidence Interval")
        self.configure(bg=BG)
        self.resizable(False, False)

        self.f_normal = pick_font(11)
        self.f_bold = pick_font(11, True)
        self.f_title = pick_font(15, True)
        self.f_small = pick_font(9)
        self.f_big = pick_font(13, True)

        self.entries = {}
        self.last_result_text = ""
        self._build()
        self.entries["n"].focus_set()
        self.bind("<Return>", lambda e: self.calculate())
        self.bind("<Escape>", lambda e: self.clear())

    # ----- layout -----
    def _build(self):
        wrap = tk.Frame(self, bg=BG, padx=22, pady=18)
        wrap.pack()

        tk.Label(wrap, text="> t-CONFIDENCE INTERVAL", bg=BG, fg=GREEN,
                 font=self.f_title).pack(anchor="w")
        tk.Label(wrap, text="CI = x̄ ± t(α/2, n-1) · s/√n", bg=BG, fg=DIM,
                 font=self.f_small).pack(anchor="w", pady=(2, 14))

        # inputs
        box = tk.Frame(wrap, bg=PANEL, highlightbackground=BORDER,
                       highlightthickness=1, padx=14, pady=12)
        box.pack(fill="x")

        fields = [
            ("n", "sample size (n)", "30"),
            ("mean", "sample mean (x̄)", ""),
            ("std", "sample std dev (s)", ""),
            ("conf", "confidence (0.99 / 99%)", "0.95"),
        ]
        for i, (key, label, default) in enumerate(fields):
            tk.Label(box, text=label, bg=PANEL, fg=FG, font=self.f_normal,
                     anchor="w", width=24).grid(row=i, column=0, sticky="w", pady=4)
            e = tk.Entry(box, bg=BG, fg=GREEN, insertbackground=GREEN,
                         relief="flat", font=self.f_normal, width=16,
                         highlightbackground=BORDER, highlightcolor=GREEN,
                         highlightthickness=1)
            e.grid(row=i, column=1, pady=4, padx=(8, 0), ipady=4)
            e.insert(0, default)
            self.entries[key] = e

        # buttons
        btns = tk.Frame(wrap, bg=BG)
        btns.pack(fill="x", pady=(12, 6))
        self._button(btns, "CALCULATE", self.calculate, GREEN).pack(side="left")
        self._button(btns, "CLEAR", self.clear, DIM).pack(side="left", padx=8)
        self._button(btns, "COPY", self.copy_result, CYAN).pack(side="left")

        # status line (errors)
        self.status = tk.Label(wrap, text="", bg=BG, fg=RED, font=self.f_small,
                               anchor="w", justify="left", wraplength=420)
        self.status.pack(fill="x", pady=(0, 6))

        # results
        res = tk.Frame(wrap, bg=PANEL, highlightbackground=BORDER,
                       highlightthickness=1, padx=14, pady=12)
        res.pack(fill="x")

        self.result_labels = {}
        rows = [
            ("df", "degrees of freedom"),
            ("t", "t-value"),
            ("se", "standard error"),
            ("me", "margin of error"),
            ("lower", "lower bound"),
            ("upper", "upper bound"),
        ]
        for i, (key, label) in enumerate(rows):
            tk.Label(res, text=label, bg=PANEL, fg=DIM, font=self.f_normal,
                     anchor="w", width=24).grid(row=i, column=0, sticky="w", pady=2)
            v = tk.Label(res, text="—", bg=PANEL, fg=FG, font=self.f_normal, anchor="e")
            v.grid(row=i, column=1, sticky="e", padx=(8, 0))
            self.result_labels[key] = v
        res.grid_columnconfigure(1, weight=1)

        tk.Frame(res, bg=BORDER, height=1).grid(row=len(rows), column=0,
                                                columnspan=2, sticky="ew", pady=8)
        self.final = tk.Label(res, text="—", bg=PANEL, fg=GREEN, font=self.f_big,
                              anchor="w")
        self.final.grid(row=len(rows) + 1, column=0, columnspan=2, sticky="w")

        tk.Label(wrap, text="BY RWIN ANDISHE", bg=BG, fg=DIM,
                 font=self.f_small).pack(anchor="e", pady=(10, 0))

    def _button(self, parent, text, cmd, color):
        b = tk.Button(parent, text=text, command=cmd, bg=BG, fg=color,
                      activebackground=color, activeforeground=BG,
                      relief="flat", font=self.f_bold, padx=14, pady=5,
                      cursor="hand2", highlightbackground=color,
                      highlightthickness=1, bd=0)
        b.bind("<Enter>", lambda e: b.config(bg=color, fg=BG))
        b.bind("<Leave>", lambda e: b.config(bg=BG, fg=color))
        return b

    # ----- actions -----
    def calculate(self):
        self.status.config(text="")
        try:
            n = int(self.entries["n"].get().strip())
            mean = float(self.entries["mean"].get().strip())
            std = float(self.entries["std"].get().strip())
            conf = parse_confidence(self.entries["conf"].get())
        except ValueError:
            self._error("Invalid input: n must be an integer; the others must be numbers.")
            return

        if n < 2:
            return self._error("n must be at least 2.")
        if std < 0:
            return self._error("Standard deviation cannot be negative.")
        if not 0 < conf < 1:
            return self._error("Confidence level must be between 0 and 1 (e.g. 0.95 or 95%).")

        r = compute_ci(n, mean, std, conf)

        self.result_labels["df"].config(text=str(r["df"]))
        self.result_labels["t"].config(text=f"{r['t']:.4f}")
        self.result_labels["se"].config(text=f"{r['se']:.4f}")
        self.result_labels["me"].config(text=f"{r['me']:.4f}")
        self.result_labels["lower"].config(text=f"{r['lower']:.4f}")
        self.result_labels["upper"].config(text=f"{r['upper']:.4f}")

        line = f"{r['conf']:.0%} CI: ({r['lower']:.4f}, {r['upper']:.4f})"
        self.final.config(text=line)

        self.last_result_text = (
            f"Sample size: {r['n']}\n"
            f"Sample mean: {r['mean']}\n"
            f"Sample standard deviation: {r['std']}\n"
            f"Confidence level: {r['conf']:.0%}\n"
            f"Degrees of freedom: {r['df']}\n"
            f"t-value: {r['t']:.4f}\n"
            f"Standard error: {r['se']:.4f}\n"
            f"Margin of error: {r['me']:.4f}\n"
            f"Lower bound: {r['lower']:.4f}\n"
            f"Upper bound: {r['upper']:.4f}\n\n"
            f"{line}"
        )

    def _error(self, msg):
        self.status.config(text="! " + msg)

    def clear(self):
        for key, e in self.entries.items():
            e.delete(0, "end")
        self.entries["conf"].insert(0, "0.95")
        for lbl in self.result_labels.values():
            lbl.config(text="—")
        self.final.config(text="—")
        self.status.config(text="")
        self.last_result_text = ""
        self.entries["n"].focus_set()

    def copy_result(self):
        if not self.last_result_text:
            return self._error("Nothing to copy yet. Run a calculation first.")
        self.clipboard_clear()
        self.clipboard_append(self.last_result_text)
        self.status.config(text="Result copied to clipboard.", fg=CYAN)
        self.after(2000, lambda: self.status.config(text="", fg=RED))


if __name__ == "__main__":
    App().mainloop()
