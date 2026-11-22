"""anova_gui.py

A graphical tool for analysis of variance (ANOVA).

  Tab "One-way ANOVA": compares the means of several groups. Every column of the
      table is one group (the column header is the group name).
  Tab "Two-way ANOVA": effects of two factors and their interaction. Every row of
      the table is one observation: level of factor A, level of factor B and the value.

Each tab shows the ANOVA table, effect sizes, assumption checks, post-hoc tests and
plots. Two-way ANOVA uses Type III sums of squares (correct for unequal group sizes).

Requirements:  pip install numpy scipy matplotlib
               (tkinter ships with Python; on Linux install the python3-tk package)
Run:           python anova_gui.py
"""

import re
import tkinter as tk
from tkinter import messagebox, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from scipy import stats

ONE_WAY_EXAMPLE = [
    ("Method A", [78, 82, 85, 80, 79, 84]),
    ("Method B", [88, 91, 86, 90, 87, 92]),
    ("Method C", [75, 77, 74, 79, 76, 73]),
]
TWO_WAY_EXAMPLE = [
    ("Low", "V1", [20.5, 19, 22, 21, 18]), ("Low", "V2", [23, 24, 25, 22, 26]),
    ("Low", "V3", [21, 20, 22, 23, 21]), ("High", "V1", [25, 24, 27, 26, 25]),
    ("High", "V2", [26, 27, 25, 28, 26]), ("High", "V3", [28, 27, 30, 29, 28]),
]


# ----------------------------------------------------------------------------
# Statistics
# ----------------------------------------------------------------------------
def to_number(text):
    """Converts text to a float (a decimal comma is accepted). Returns None on failure."""
    try:
        value = float(text.strip().replace(",", "."))
    except ValueError:
        return None
    return value if value == value and abs(value) != float("inf") else None


def fmt_p(p):
    return "<0.0001" if p < 1e-4 else f"{p:.4f}"


def tukey_table(names, estimates, se_difference, df_error):
    """Tukey-Kramer comparisons between all pairs of estimates.

    se_difference[i][j] is the standard error of (estimate j - estimate i).
    Returns rows (comparison, difference, lower, upper, adjusted p), sorted by p.
    """
    k = len(names)
    q_critical = stats.studentized_range.ppf(0.95, k, df_error)
    rows = []
    for i in range(k):
        for j in range(i + 1, k):
            difference = estimates[j] - estimates[i]
            se_q = se_difference[i][j] / np.sqrt(2)
            q = abs(difference) / se_q
            rows.append((f"{names[j]} - {names[i]}", difference,
                         difference - q_critical * se_q, difference + q_critical * se_q,
                         float(stats.studentized_range.sf(q, k, df_error))))
    return sorted(rows, key=lambda row: row[4])


def tukey_pairs(names, means, counts, mse, df_error):
    """Tukey HSD for group means with the pooled error (one-way ANOVA)."""
    se = [[np.sqrt(mse * (1 / counts[i] + 1 / counts[j])) for j in range(len(names))]
          for i in range(len(names))]
    return tukey_table(names, means, se, df_error)


def welch_anova(data):
    """Welch's ANOVA (unequal variances). Returns (F, df1, df2, p) or None."""
    k = len(data)
    n = np.array([len(d) for d in data], float)
    means = np.array([d.mean() for d in data])
    variances = np.array([d.var(ddof=1) for d in data])
    if np.any(variances == 0):
        return None
    weights = n / variances
    weight_sum = weights.sum()
    weighted_mean = (weights * means).sum() / weight_sum
    tmp = (((1 - weights / weight_sum) ** 2) / (n - 1)).sum()
    f = ((weights * (means - weighted_mean) ** 2).sum() / (k - 1)) / (1 + 2 * (k - 2) / (k ** 2 - 1) * tmp)
    df2 = (k ** 2 - 1) / (3 * tmp)
    return float(f), k - 1, float(df2), float(stats.f.sf(f, k - 1, df2))


def one_way_anova(groups):
    """groups: list of (name, values). Returns a dictionary with all results."""
    names = [name for name, _ in groups]
    data = [np.array(values, float) for _, values in groups]
    k = len(data)
    counts = np.array([len(d) for d in data])
    n = int(counts.sum())
    means = np.array([d.mean() for d in data])
    sds = np.array([d.std(ddof=1) for d in data])
    grand_mean = np.concatenate(data).mean()

    ss_between = float((counts * (means - grand_mean) ** 2).sum())
    ss_within = float(sum(((d - d.mean()) ** 2).sum() for d in data))
    if ss_within == 0:
        raise ValueError("There is no variation inside the groups, so ANOVA cannot be computed.")
    df_between, df_within = k - 1, n - k
    ms_between, ms_within = ss_between / df_between, ss_within / df_within
    f_value = ms_between / ms_within
    p_value = float(stats.f.sf(f_value, df_between, df_within))

    residuals = np.concatenate([d - d.mean() for d in data])
    shapiro = stats.shapiro(residuals) if len(residuals) >= 3 else None
    brown_forsythe = stats.levene(*data, center="median")
    kruskal = stats.kruskal(*data)

    return dict(
        names=names, data=data, k=k, n=n, counts=counts, means=means, sds=sds,
        ss_between=ss_between, ss_within=ss_within, df_between=df_between, df_within=df_within,
        ms_between=ms_between, ms_within=ms_within, f=f_value, p=p_value,
        eta2=ss_between / (ss_between + ss_within),
        omega2=max(0.0, (ss_between - df_between * ms_within) / (ss_between + ss_within + ms_within)),
        residuals=residuals, shapiro=shapiro, brown_forsythe=brown_forsythe,
        welch=welch_anova(data), kruskal=kruskal,
        tukey=tukey_pairs(names, means, counts, ms_within, df_within) if k >= 3 else None,
    )


def effect_coding(index, levels):
    """Sum-to-zero coding of a factor: n rows by (levels - 1) columns."""
    codes = np.zeros((len(index), levels - 1))
    for row, level in enumerate(index):
        if level < levels - 1:
            codes[row, level] = 1.0
        else:
            codes[row, :] = -1.0
    return codes


def simple_effect(means, counts, mse, df_error):
    """Test that the cell means in one row (or column) are equal, using the pooled error."""
    weighted_mean = (counts * means).sum() / counts.sum()
    ss = float((counts * (means - weighted_mean) ** 2).sum())
    df1 = len(means) - 1
    f = (ss / df1) / mse
    return f, df1, float(stats.f.sf(f, df1, df_error))


def two_way_anova(rows, a_name, b_name):
    """rows: list of (level of A, level of B, value). Type III ANOVA with interaction."""
    a_levels = list(dict.fromkeys(r[0] for r in rows))
    b_levels = list(dict.fromkeys(r[1] for r in rows))
    na, nb = len(a_levels), len(b_levels)
    if na < 2 or nb < 2:
        raise ValueError("Each factor needs at least 2 levels.")

    a_index = np.array([a_levels.index(r[0]) for r in rows])
    b_index = np.array([b_levels.index(r[1]) for r in rows])
    y = np.array([r[2] for r in rows], float)
    n = len(y)

    counts = np.zeros((na, nb), int)
    for i, j in zip(a_index, b_index):
        counts[i, j] += 1
    missing = [f"{a_levels[i]} / {b_levels[j]}" for i in range(na) for j in range(nb) if counts[i, j] == 0]
    if missing:
        raise ValueError("Every combination of the two factors needs data. Missing: " + ", ".join(missing[:5]))
    if counts.min() < 2:
        raise ValueError("Each combination of the factors needs at least 2 values.")

    A = effect_coding(a_index, na)
    B = effect_coding(b_index, nb)
    AB = np.column_stack([A[:, i] * B[:, j] for i in range(na - 1) for j in range(nb - 1)])
    ones = np.ones((n, 1))

    def fit(*blocks):
        X = np.hstack([ones, *blocks])
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        residual = y - X @ beta
        return float(residual @ residual), residual

    rss_full, residuals = fit(A, B, AB)
    if rss_full == 0:
        raise ValueError("There is no variation inside the cells, so ANOVA cannot be computed.")
    df_error = n - na * nb
    mse = rss_full / df_error

    effects = []
    for label, df, reduced in ((a_name, na - 1, fit(B, AB)[0]), (b_name, nb - 1, fit(A, AB)[0]),
                               (f"{a_name} x {b_name}", (na - 1) * (nb - 1), fit(A, B)[0])):
        ss = reduced - rss_full
        f = (ss / df) / mse
        effects.append(dict(label=label, df=df, ss=ss, ms=ss / df, f=f,
                            p=float(stats.f.sf(f, df, df_error)), partial_eta2=ss / (ss + rss_full)))

    means = np.zeros((na, nb))
    sds = np.zeros((na, nb))
    cells = []
    for i in range(na):
        for j in range(nb):
            values = y[(a_index == i) & (b_index == j)]
            means[i, j], sds[i, j] = values.mean(), values.std(ddof=1)
            cells.append(values)

    result = dict(
        a_name=a_name, b_name=b_name, a_levels=a_levels, b_levels=b_levels, na=na, nb=nb, n=n,
        counts=counts, balanced=len(set(counts.flatten())) == 1, means=means, sds=sds,
        effects=effects, ss_error=rss_full, df_error=df_error, ms_error=mse, residuals=residuals,
        shapiro=stats.shapiro(residuals) if n >= 3 else None,
        brown_forsythe=stats.levene(*cells, center="median"),
        simple_b_within_a=None, simple_a_within_b=None, tukey_a=None, tukey_b=None,
    )

    if effects[2]["p"] < 0.05:
        result["simple_b_within_a"] = [simple_effect(means[i, :], counts[i, :], mse, df_error) for i in range(na)]
        result["simple_a_within_b"] = [simple_effect(means[:, j], counts[:, j], mse, df_error) for j in range(nb)]

    # Post-hoc comparisons of the levels of each factor use the estimated marginal means
    # (the average of the cell means), which matches the Type III tests. For a balanced
    # design they are the ordinary marginal means.
    inverse_counts = 1.0 / counts
    for key, label_key, marginal, inverse, other_levels, effect in (
            ("tukey_a", "a_levels", means.mean(axis=1), inverse_counts.sum(axis=1), nb, effects[0]),
            ("tukey_b", "b_levels", means.mean(axis=0), inverse_counts.sum(axis=0), na, effects[1])):
        labels = result[label_key]
        result["marginal_" + key[-1]] = marginal
        if len(labels) >= 3 and effect["p"] < 0.05:
            se = [[np.sqrt(mse / other_levels ** 2 * (inverse[i] + inverse[j])) for j in range(len(labels))]
                  for i in range(len(labels))]
            result[key] = tukey_table(labels, marginal, se, df_error)
    return result


# ----------------------------------------------------------------------------
# Result text
# ----------------------------------------------------------------------------
def tukey_text(rows):
    width = max(len(row[0]) for row in rows)
    lines = [f"  {'comparison':<{width}}  {'difference':>10} {'lower':>9} {'upper':>9} {'adj. p':>9}"]
    for name, diff, low, high, p in rows:
        lines.append(f"  {name:<{width}}  {diff:10.3f} {low:9.3f} {high:9.3f} {fmt_p(p):>9}")
    return lines


def one_way_text(r):
    width = max(len(name) for name in r["names"] + ["Residual", "group"])
    lines = [f"One-way ANOVA: {r['k']} groups, n = {r['n']}", "", "Group summary",
             f"  {'group':<{width}} {'n':>4} {'mean':>10} {'sd':>9}"]
    for name, count, mean, sd in zip(r["names"], r["counts"], r["means"], r["sds"]):
        lines.append(f"  {name:<{width}} {count:4d} {mean:10.3f} {sd:9.3f}")
    lines += ["", "ANOVA table",
              f"  {'Source':<{width}} {'df':>4} {'SS':>10} {'MS':>10} {'F':>9} {'p':>9}",
              f"  {'Groups':<{width}} {r['df_between']:4d} {r['ss_between']:10.3f} {r['ms_between']:10.3f}"
              f" {r['f']:9.3f} {fmt_p(r['p']):>9}",
              f"  {'Residual':<{width}} {r['df_within']:4d} {r['ss_within']:10.3f} {r['ms_within']:10.3f}",
              "", f"Eta-squared = {r['eta2']:.3f}, omega-squared = {r['omega2']:.3f} "
                  "(share of the variation explained by the groups)"]
    lines.append("Result: " + ("at least one group mean differs from the others (p < 0.05)."
                               if r["p"] < 0.05 else "no significant difference between the group means (p >= 0.05)."))
    lines += ["", "Assumption checks"]
    if r["shapiro"] is not None:
        lines.append(f"  Shapiro-Wilk (normal residuals): W = {r['shapiro'].statistic:.4f}, p = {r['shapiro'].pvalue:.4f}")
    bf = r["brown_forsythe"]
    lines.append(f"  Brown-Forsythe (equal variances): F = {bf.statistic:.3f}, p = {bf.pvalue:.4f}")
    lines.append("  A p-value below 0.05 means that assumption is doubtful.")
    lines += ["", "Robust alternatives"]
    if r["welch"] is not None:
        f, df1, df2, p = r["welch"]
        lines.append(f"  Welch ANOVA (unequal variances): F = {f:.3f} (df {df1}, {df2:.2f}), p = {fmt_p(p)}")
    lines.append(f"  Kruskal-Wallis (no normality needed): H = {r['kruskal'].statistic:.3f}, p = {fmt_p(r['kruskal'].pvalue)}")
    if r["tukey"] is not None:
        if r["p"] < 0.05:
            lines += ["", "Tukey HSD post-hoc comparisons (95% family-wise)"] + tukey_text(r["tukey"])
        else:
            lines += ["", "The ANOVA is not significant, so post-hoc comparisons are not needed."]
    return "\n".join(lines)


def two_way_text(r):
    a, b = r["a_name"], r["b_name"]
    lines = [f"Two-way ANOVA: {a} ({r['na']} levels) x {b} ({r['nb']} levels), n = {r['n']}"]
    sizes = sorted(set(r["counts"].flatten()))
    lines.append("Design: balanced, " + f"{sizes[0]} values per cell" if r["balanced"]
                 else f"Design: unbalanced ({sizes[0]} to {sizes[-1]} values per cell)")
    cell_text = [[f"{r['means'][i, j]:.2f} ({r['sds'][i, j]:.2f})" for j in range(r["nb"])] for i in range(r["na"])]
    label_width = max(len(x) for x in r["a_levels"] + [a])
    col_width = max(len(x) for row in cell_text for x in row + r["b_levels"]) + 1
    lines += ["", f"Cell means (standard deviation); rows = {a}, columns = {b}",
              f"  {'':<{label_width}} " + " ".join(f"{x:>{col_width}}" for x in r["b_levels"])]
    for level, row in zip(r["a_levels"], cell_text):
        lines.append(f"  {level:<{label_width}} " + " ".join(f"{x:>{col_width}}" for x in row))

    width = max(len(e["label"]) for e in r["effects"] + [dict(label="Residual")])
    lines += ["", "ANOVA table (Type III)",
              f"  {'Effect':<{width}} {'df':>4} {'SS':>10} {'MS':>10} {'F':>9} {'p':>9} {'partial eta2':>13}"]
    for e in r["effects"]:
        lines.append(f"  {e['label']:<{width}} {e['df']:4d} {e['ss']:10.3f} {e['ms']:10.3f} {e['f']:9.3f}"
                     f" {fmt_p(e['p']):>9} {e['partial_eta2']:13.3f}")
    lines.append(f"  {'Residual':<{width}} {r['df_error']:4d} {r['ss_error']:10.3f} {r['ms_error']:10.3f}")

    lines += ["", "Interpretation"]
    for e in r["effects"]:
        lines.append(f"  {e['label']:<{width}}  " + ("significant    " if e["p"] < 0.05 else "not significant")
                     + f" (p = {fmt_p(e['p'])})")
    if r["effects"][2]["p"] < 0.05:
        lines += ["", "The interaction is significant: the effect of one factor depends on the level of the other.",
                  "Interpret the main effects with caution; see the interaction plot and the simple effects below."]

    lines += ["", "Assumption checks"]
    if r["shapiro"] is not None:
        lines.append(f"  Shapiro-Wilk (normal residuals): W = {r['shapiro'].statistic:.4f}, p = {r['shapiro'].pvalue:.4f}")
    bf = r["brown_forsythe"]
    lines.append(f"  Brown-Forsythe (equal variances across the cells): F = {bf.statistic:.3f}, p = {bf.pvalue:.4f}")
    lines.append("  A p-value below 0.05 means that assumption is doubtful.")

    if r["simple_b_within_a"] is not None:
        for title, levels, tests in ((f"Simple effects of {b} within each level of {a}", r["a_levels"], r["simple_b_within_a"]),
                                     (f"Simple effects of {a} within each level of {b}", r["b_levels"], r["simple_a_within_b"])):
            lines += ["", title]
            for level, (f, df1, p) in zip(levels, tests):
                lines.append(f"  {level:<{label_width}}  F({df1}, {r['df_error']}) = {f:8.3f}, p = {fmt_p(p)}")
    for key, label, levels in (("tukey_a", a, r["a_levels"]), ("tukey_b", b, r["b_levels"])):
        if r[key] is not None:
            marginal = r["marginal_" + key[-1]]
            lines += ["", f"Tukey HSD comparisons for {label} (95% family-wise)"]
            if not r["balanced"]:
                lines.append("  (unbalanced design: levels are compared as estimated marginal means,")
                lines.append("   i.e. averages of the cell means, which matches the Type III tests)")
            lines.append("  marginal means: " + ", ".join(f"{name} = {value:.3f}" for name, value in zip(levels, marginal)))
            lines += tukey_text(r[key])
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# Plots
# ----------------------------------------------------------------------------
def style_qq_axes(axes, residuals):
    stats.probplot(residuals, dist="norm", plot=axes)
    points, line = axes.get_lines()[0], axes.get_lines()[1]
    points.set_markerfacecolor("steelblue")
    points.set_markeredgecolor("steelblue")
    line.set_color("red")
    axes.set_title("Normal Q-Q plot of residuals")
    axes.grid(alpha=0.3)


def draw_one_way(figure, r):
    figure.clear()
    left = figure.add_subplot(1, 2, 1)
    right = figure.add_subplot(1, 2, 2)
    positions = range(1, r["k"] + 1)

    boxes = left.boxplot(r["data"], widths=0.55, patch_artist=True, showfliers=False)
    for box in boxes["boxes"]:
        box.set_facecolor("#9ecae1")
    for median in boxes["medians"]:
        median.set_color("black")
        median.set_linewidth(2)
    generator = np.random.default_rng(1)
    for position, values in zip(positions, r["data"]):
        left.scatter(position + generator.uniform(-0.12, 0.12, len(values)), values, s=18,
                     color="#444444", alpha=0.7, zorder=3)
    left.scatter(positions, r["means"], marker="D", color="red", s=60, zorder=4, label="Group mean")
    left.set_xticks(list(positions))
    left.set_xticklabels(r["names"], rotation=0 if r["k"] <= 5 else 30)
    left.set_ylabel("Value")
    left.set_title(f"ANOVA: F = {r['f']:.2f}, p = {fmt_p(r['p'])}")
    left.legend(loc="best")
    left.grid(alpha=0.3)

    style_qq_axes(right, r["residuals"])
    figure.tight_layout()


def draw_two_way(figure, r):
    figure.clear()
    left = figure.add_subplot(1, 2, 1)
    right = figure.add_subplot(1, 2, 2)
    positions = np.arange(r["na"])
    standard_errors = r["sds"] / np.sqrt(r["counts"])
    for j, level in enumerate(r["b_levels"]):
        left.errorbar(positions, r["means"][:, j], yerr=standard_errors[:, j], marker="o", linewidth=2,
                      capsize=3, label=level)
    left.set_xticks(positions)
    left.set_xticklabels(r["a_levels"])
    left.set_xlim(-0.3, r["na"] - 0.7)
    left.set_xlabel(r["a_name"])
    left.set_ylabel("Mean value")
    left.set_title("Interaction plot (mean +/- SE)")
    left.legend(title=r["b_name"], loc="best")
    left.grid(alpha=0.3)

    style_qq_axes(right, r["residuals"])
    figure.tight_layout()


# ----------------------------------------------------------------------------
# Editable table widget
# ----------------------------------------------------------------------------
class EntryGrid(ttk.Frame):
    """A scrollable table of entry cells with editable column headers."""

    def __init__(self, master, headers, rows, cell_width=11, height=320):
        super().__init__(master)
        self.cell_width = cell_width
        self.header_entries = []
        self.cells = []

        self.header_canvas = tk.Canvas(self, height=30, highlightthickness=0)
        self.header_frame = ttk.Frame(self.header_canvas)
        self.header_canvas.create_window((0, 0), window=self.header_frame, anchor="nw")

        self.canvas = tk.Canvas(self, height=height, highlightthickness=0)
        self.body = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.body, anchor="nw")

        self.vscroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.hscroll = ttk.Scrollbar(self, orient="horizontal", command=self._xview)
        self.canvas.configure(yscrollcommand=self.vscroll.set, xscrollcommand=self._on_xscroll)

        self.header_canvas.grid(row=0, column=0, sticky="ew")
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.vscroll.grid(row=1, column=1, sticky="ns")
        self.hscroll.grid(row=2, column=0, sticky="ew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.body.bind("<Configure>", self._update_regions)

        self.set_data(headers, [], rows)

    # -- scrolling ----------------------------------------------------------
    def _xview(self, *args):
        self.canvas.xview(*args)
        self.header_canvas.xview(*args)

    def _on_xscroll(self, first, last):
        self.hscroll.set(first, last)
        self.header_canvas.xview_moveto(first)

    def _update_regions(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        width = self.body.winfo_reqwidth()
        self.header_canvas.configure(scrollregion=(0, 0, width, 30))

    # -- content ------------------------------------------------------------
    def set_data(self, headers, data_rows, minimum_rows):
        for widget in list(self.header_frame.winfo_children()) + list(self.body.winfo_children()):
            widget.destroy()
        self.header_entries = []
        self.cells = []

        ttk.Label(self.header_frame, text="#", width=4, anchor="center").grid(row=0, column=0, padx=1)
        for c, header in enumerate(headers):
            entry = ttk.Entry(self.header_frame, width=self.cell_width, justify="center")
            entry.insert(0, header)
            entry.grid(row=0, column=c + 1, padx=1)
            self.header_entries.append(entry)

        for row in data_rows:
            self.add_row(row)
        while len(self.cells) < minimum_rows:
            self.add_row()
        self.canvas.yview_moveto(0)

    def add_row(self, values=None):
        r = len(self.cells)
        ttk.Label(self.body, text=str(r + 1), width=4, anchor="center").grid(row=r, column=0, padx=1, pady=1)
        entries = []
        for c in range(len(self.header_entries)):
            entry = ttk.Entry(self.body, width=self.cell_width)
            entry.grid(row=r, column=c + 1, padx=1, pady=1)
            if values is not None and c < len(values):
                entry.insert(0, str(values[c]))
            entry.bind("<Return>", lambda event, rr=r, cc=c: self.focus_cell(rr + 1, cc))
            entries.append(entry)
        self.cells.append(entries)

    def add_column(self, name):
        self.set_data(self.get_headers() + [name], self.get_rows(), len(self.cells))

    def focus_cell(self, row, column):
        if row >= len(self.cells):
            self.add_row()
            self.canvas.update_idletasks()
            self.canvas.yview_moveto(1)
        self.cells[row][column].focus_set()

    def get_headers(self):
        return [entry.get() for entry in self.header_entries]

    def get_rows(self):
        return [[entry.get() for entry in row] for row in self.cells]

    def column_count(self):
        return len(self.header_entries)


# ----------------------------------------------------------------------------
# Tabs
# ----------------------------------------------------------------------------
class AnovaTab(ttk.Frame):
    """Left: data table and buttons. Right: plot and text results."""

    def __init__(self, master, headers, rows, cell_width):
        super().__init__(master)
        left = ttk.Frame(self, padding=8)
        left.pack(side="left", fill="y")
        self.table = EntryGrid(left, headers, rows, cell_width=cell_width)
        self.table.pack(fill="both", expand=True)
        self.buttons = ttk.Frame(left)
        self.buttons.pack(fill="x", pady=(8, 0))
        self.buttons.columnconfigure((0, 1), weight=1)
        self.build_buttons()
        ttk.Button(left, text="Calculate  (Ctrl+Enter)", command=self.calculate).pack(fill="x", pady=(8, 0), ipady=4)

        right = ttk.Frame(self, padding=(0, 8, 8, 8))
        right.pack(side="left", fill="both", expand=True)
        self.figure = Figure(figsize=(7, 3.6), dpi=100)
        self.plot_canvas = FigureCanvasTkAgg(self.figure, master=right)
        self.plot_canvas.get_tk_widget().pack(fill="both", expand=True)

        text_frame = ttk.Frame(right)
        text_frame.pack(fill="both", expand=False, pady=(8, 0))
        self.results = tk.Text(text_frame, height=17, font="TkFixedFont", wrap="none", state="disabled",
                               background="#f2f2f2", relief="flat", padx=8, pady=6)
        scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.results.yview)
        self.results.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.results.pack(side="left", fill="both", expand=True)
        self.show_placeholder()

    def add_button(self, text, command, row, column):
        ttk.Button(self.buttons, text=text, command=command).grid(row=row, column=column, sticky="ew", padx=2, pady=2)

    def show_placeholder(self):
        self.figure.clear()
        axes = self.figure.add_subplot(1, 1, 1)
        axes.text(0.5, 0.5, "Enter the data in the table and press Calculate", ha="center", va="center",
                  color="gray", transform=axes.transAxes)
        axes.set_axis_off()
        self.plot_canvas.draw()

    def set_results(self, text):
        self.results.configure(state="normal")
        self.results.delete("1.0", "end")
        self.results.insert("1.0", text)
        self.results.configure(state="disabled")

    def clear_all(self):
        self.reset_table()
        self.show_placeholder()
        self.set_results("")

    def run(self, compute, text_function, draw_function):
        try:
            result = compute()
        except ValueError as error:
            messagebox.showerror("Cannot calculate", str(error))
            return None
        draw_function(self.figure, result)
        self.plot_canvas.draw()
        self.set_results(text_function(result))
        return result


class OneWayTab(AnovaTab):
    def __init__(self, master):
        super().__init__(master, ["Group 1", "Group 2", "Group 3"], 14, cell_width=10)

    def build_buttons(self):
        self.add_button("Add row", self.table.add_row, 0, 0)
        self.add_button("Add group", lambda: self.table.add_column(f"Group {self.table.column_count() + 1}"), 0, 1)
        self.add_button("Paste from clipboard", self.paste, 1, 0)
        self.add_button("Load example", self.load_example, 1, 1)
        self.add_button("Clear", self.clear_all, 2, 0)

    def reset_table(self):
        self.table.set_data(["Group 1", "Group 2", "Group 3"], [], 14)

    def load_example(self):
        names = [name for name, _ in ONE_WAY_EXAMPLE]
        length = max(len(values) for _, values in ONE_WAY_EXAMPLE)
        rows = [[values[i] if i < len(values) else "" for _, values in ONE_WAY_EXAMPLE] for i in range(length)]
        self.table.set_data(names, rows, 14)

    def paste(self):
        try:
            text = self.clipboard_get()
        except tk.TclError:
            messagebox.showinfo("Paste", "The clipboard is empty.")
            return
        headers, rows = parse_wide_clipboard(text)
        if not rows:
            messagebox.showwarning("Paste", "No data was found in the clipboard.")
            return
        self.table.set_data(headers, rows, 14)

    def read_groups(self):
        headers = self.table.get_headers()
        rows = self.table.get_rows()
        groups, used = [], set()
        for c, header in enumerate(headers):
            name = header.strip() or f"Group {c + 1}"
            values = []
            for number, row in enumerate(rows, start=1):
                text = row[c].strip()
                if not text:
                    continue
                value = to_number(text)
                if value is None:
                    raise ValueError(f"{name}, row {number}: '{text}' is not a number.")
                values.append(value)
            if not values:
                continue
            base, suffix = name, 2
            while name in used:
                name, suffix = f"{base} ({suffix})", suffix + 1
            used.add(name)
            groups.append((name, values))
        if len(groups) < 2:
            raise ValueError("Enter values for at least 2 groups.")
        for name, values in groups:
            if len(values) < 2:
                raise ValueError(f"{name} needs at least 2 values.")
        return groups

    def calculate(self):
        return self.run(lambda: one_way_anova(self.read_groups()), one_way_text, draw_one_way)


class TwoWayTab(AnovaTab):
    def __init__(self, master):
        super().__init__(master, ["Factor A", "Factor B", "Value"], 18, cell_width=11)

    def build_buttons(self):
        self.add_button("Add row", self.table.add_row, 0, 0)
        self.add_button("Clear", self.clear_all, 0, 1)
        self.add_button("Paste from clipboard", self.paste, 1, 0)
        self.add_button("Load example", self.load_example, 1, 1)

    def reset_table(self):
        self.table.set_data(["Factor A", "Factor B", "Value"], [], 18)

    def load_example(self):
        rows = [(a, b, v) for a, b, values in TWO_WAY_EXAMPLE for v in values]
        self.table.set_data(["Fertilizer", "Variety", "Yield"], rows, 18)

    def paste(self):
        try:
            text = self.clipboard_get()
        except tk.TclError:
            messagebox.showinfo("Paste", "The clipboard is empty.")
            return
        headers, rows = parse_long_clipboard(text)
        if not rows:
            messagebox.showwarning("Paste", "No rows with three columns (A, B, value) were found.")
            return
        self.table.set_data(headers, rows, 18)

    def read_rows(self):
        headers = self.table.get_headers()
        a_name = headers[0].strip() or "Factor A"
        b_name = headers[1].strip() or "Factor B"
        if a_name == b_name:
            raise ValueError("The two factors need different names (edit the column headers).")
        rows = []
        for number, row in enumerate(self.table.get_rows(), start=1):
            a, b, text = (cell.strip() for cell in row)
            if not (a or b or text):
                continue
            if not (a and b and text):
                raise ValueError(f"Row {number} is incomplete: fill the level of A, the level of B and the value.")
            value = to_number(text)
            if value is None:
                raise ValueError(f"Row {number}: '{text}' is not a number.")
            rows.append((a, b, value))
        if not rows:
            raise ValueError("The table is empty.")
        return rows, a_name, b_name

    def calculate(self):
        def compute():
            rows, a_name, b_name = self.read_rows()
            return two_way_anova(rows, a_name, b_name)
        return self.run(compute, two_way_text, draw_two_way)


# ----------------------------------------------------------------------------
# Clipboard parsing
# ----------------------------------------------------------------------------
def split_line(line):
    """Splits a clipboard line on tabs, semicolons, commas or whitespace."""
    line = line.strip()
    for separator in ("\t", ";"):
        if separator in line:
            return [part.strip() for part in line.split(separator)]
    if "," in line:
        return [part.strip() for part in line.split(",")]
    return line.split()


def parse_wide_clipboard(text):
    """Columns = groups. A first row with non-numeric cells is used as the header."""
    lines = [split_line(line) for line in text.splitlines() if line.strip()]
    if not lines:
        return [], []
    width = max(len(line) for line in lines)
    lines = [line + [""] * (width - len(line)) for line in lines]
    has_header = any(cell and to_number(cell) is None for cell in lines[0])
    headers = lines[0] if has_header else [f"Group {i + 1}" for i in range(width)]
    headers = [h or f"Group {i + 1}" for i, h in enumerate(headers)]
    return headers, (lines[1:] if has_header else lines)


def parse_long_clipboard(text):
    """Rows of (level of A, level of B, value); an optional header row is skipped."""
    rows = [split_line(line) for line in text.splitlines() if line.strip()]
    rows = [row[:3] for row in rows if len(row) >= 3]
    headers = ["Factor A", "Factor B", "Value"]
    if rows and to_number(rows[0][2]) is None:
        headers = rows[0]
        rows = rows[1:]
    return headers, rows


# ----------------------------------------------------------------------------
# Application window
# ----------------------------------------------------------------------------
class AnovaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ANOVA Tool")
        self.geometry("1400x820")
        self.minsize(1100, 680)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=6, pady=6)
        self.one_way = OneWayTab(self.notebook)
        self.two_way = TwoWayTab(self.notebook)
        self.notebook.add(self.one_way, text="One-way ANOVA")
        self.notebook.add(self.two_way, text="Two-way ANOVA")

        self.bind("<Control-Return>", lambda event: self.current_tab().calculate())
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind_all(sequence, self._on_mousewheel)

    def current_tab(self):
        return self.nametowidget(self.notebook.select())

    def _on_mousewheel(self, event):
        widget = self.winfo_containing(event.x_root, event.y_root)
        while widget is not None and not isinstance(widget, EntryGrid):
            widget = widget.master
        if widget is None:
            return
        if event.num == 4:
            step = -1
        elif event.num == 5:
            step = 1
        else:
            step = -1 if event.delta > 0 else 1
        widget.canvas.yview_scroll(step, "units")


if __name__ == "__main__":
    AnovaApp().mainloop()
