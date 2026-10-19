import math
import tkinter as tk
from scipy import stats


def calculate():
    # gereftan voroodi ha az kadr ha
    n = int(entry_n.get())
    sample_mean = float(entry_mean.get())
    sample_std = float(entry_std.get())
    confidence_level = float(entry_conf.get())

    # DARAGE AZADI
    df = n - 1

    # HESAB KARDAN T / JADVAL T
    alpha = 1 - confidence_level
    t_critical = stats.t.ppf(1 - alpha / 2, df)

    standard_error = sample_std / math.sqrt(n)
    margin_error = t_critical * standard_error

    lower = sample_mean - margin_error  # KAMTARIN
    upper = sample_mean + margin_error  # BISHTARIN

    # CHAP natije
    result = (
        f"Degrees of freedom: {df}\n"
        f"t-value: {t_critical:.4f}\n"
        f"Standard error: {standard_error:.4f}\n"
        f"Margin of error: {margin_error:.4f}\n"
        f"Lower bound: {lower:.4f}\n"
        f"Upper bound: {upper:.4f}\n\n"
        f"{confidence_level:.0%} Confidence Interval:\n"
        f"({lower:.4f}, {upper:.4f})"
    )
    result_label.config(text=result)


# SAKHTAN PANJEREH
window = tk.Tk()
window.title("Confidence Interval")

tk.Label(window, text="sample size (n):").grid(row=0, column=0, padx=10, pady=5)
entry_n = tk.Entry(window)
entry_n.grid(row=0, column=1, padx=10)

tk.Label(window, text="sample mean (x-bar):").grid(row=1, column=0, padx=10, pady=5)
entry_mean = tk.Entry(window)
entry_mean.grid(row=1, column=1, padx=10)

tk.Label(window, text="sample std (s):").grid(row=2, column=0, padx=10, pady=5)
entry_std = tk.Entry(window)
entry_std.grid(row=2, column=1, padx=10)

tk.Label(window, text="confidence level (0.95):").grid(row=3, column=0, padx=10, pady=5)
entry_conf = tk.Entry(window)
entry_conf.grid(row=3, column=1, padx=10)

tk.Button(window, text="Calculate", command=calculate).grid(row=4, column=0, columnspan=2, pady=10)

result_label = tk.Label(window, text="", justify="left")
result_label.grid(row=5, column=0, columnspan=2, padx=10, pady=10)

window.mainloop()


####  BY RWIN ANDISHE ####
