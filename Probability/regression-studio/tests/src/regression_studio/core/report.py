"""Text formatting of results for the UI and for exported reports."""

from __future__ import annotations

import math

import numpy as np

from .models import FitResult, Prediction


def fmt(value: float | None, digits: int = 6) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    if math.isinf(value):
        return "inf" if value > 0 else "-inf"
    return f"{value:.{digits}g}"


def fmt_p(p: float) -> str:
    if math.isnan(p):
        return "-"
    return "<0.0001" if p < 1e-4 else f"{p:.4f}"


def coefficient_headers(result: FitResult) -> list[str]:
    pct = f"{result.level * 100:g}%"
    se = "Std. error (HC3)" if result.spec.robust else "Std. error"
    return ["Term", "Estimate", se, "t", "p-value", f"{pct} CI low", f"{pct} CI high"]


def coefficient_rows(result: FitResult) -> list[list[str]]:
    return [
        [
            result.term_names[i],
            fmt(float(result.coef[i])),
            fmt(float(result.std_err[i])),
            fmt(float(result.t_stat[i]), 4),
            fmt_p(float(result.p_values[i])),
            fmt(float(result.ci_low[i])),
            fmt(float(result.ci_high[i])),
        ]
        for i in range(len(result.term_names))
    ]


def _grid(headers: list[str], rows: list[list[str]]) -> list[str]:
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    lines = ["  ".join(h.ljust(w) if i == 0 else h.rjust(w) for i, (h, w) in enumerate(zip(headers, widths)))]
    for row in rows:
        lines.append("  ".join(c.ljust(w) if i == 0 else c.rjust(w) for i, (c, w) in enumerate(zip(row, widths))))
    return lines


def build_report(r: FitResult) -> str:
    out: list[str] = ["REGRESSION REPORT", "=" * 17, ""]

    def kv(label: str, value: str) -> None:
        out.append(f"{label:<26}{value}")

    kv("Model", r.spec.describe())
    kv("Response", r.spec.y_col)
    kv("Predictors", ", ".join(r.spec.x_cols))
    skipped = f" ({r.n_dropped} incomplete rows skipped)" if r.n_dropped else ""
    kv("Observations", f"{r.n}{skipped}")
    out += ["", "Equation", f"  {r.equation}", "", "Fit statistics"]
    kv("  R-squared", fmt(r.r2))
    kv("  Adjusted R-squared", fmt(r.adj_r2))
    kv("  RMSE", fmt(r.rmse))
    kv("  MAE", fmt(r.mae))
    kv("  Residual std. error", f"{fmt(r.sigma)} on {r.dof} dof")
    kv("  F-statistic", f"{fmt(r.f_stat)} (p {fmt_p(r.f_p)})")
    out += ["", "Coefficients", *_grid(coefficient_headers(r), coefficient_rows(r))]
    out += ["", "Residual diagnostics"]
    kv("  Durbin-Watson", f"{fmt(r.durbin_watson, 4)} (assumes rows are in sequence order)")
    kv("  Jarque-Bera", f"{fmt(r.jb_stat, 4)} (p {fmt_p(r.jb_p)})")
    kv("  Breusch-Pagan", f"{fmt(r.bp_stat, 4)} on {r.bp_df} dof (p {fmt_p(r.bp_p)})")
    flagged = sum(1 for f in r.flags if f)
    kv("  Flagged points", f"{flagged} of {r.n} (leverage, outlier or influential)")
    if r.rows_excluded.size:
        shown = ", ".join(str(int(i) + 1) for i in np.sort(r.rows_excluded)[:20])
        more = " ..." if r.rows_excluded.size > 20 else ""
        kv("  Excluded rows", f"{r.rows_excluded.size}: {shown}{more}")
    if r.notes:
        out += ["", "Notes"] + [f"  - {note}" for note in r.notes]
    return "\n".join(out) + "\n"


def format_prediction(r: FitResult, pred: Prediction) -> str:
    pct = f"{pred.level * 100:g}%"
    names = r.spec.x_cols
    lines: list[str] = []
    for i in range(pred.yhat.size):
        inputs = ", ".join(f"{n}={fmt(float(v))}" for n, v in zip(names, pred.x[i]))
        line = (
            f"{inputs}\n  {r.spec.y_col} = {fmt(float(pred.yhat[i]))}\n"
            f"  {pct} CI [{fmt(float(pred.ci_low[i]))}, {fmt(float(pred.ci_high[i]))}]\n"
            f"  {pct} PI [{fmt(float(pred.pi_low[i]))}, {fmt(float(pred.pi_high[i]))}]"
        )
        if pred.extrapolated[i]:
            line += "\n  outside the range of the data"
        lines.append(line)
    return "\n".join(lines)
