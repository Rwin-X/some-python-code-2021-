"""Regression engine: fitting, prediction and model comparison. No Qt imports.

Every model is an ordinary least squares fit of a design matrix. The
exponential and power models are fitted on log-transformed data; their
coefficient statistics therefore describe the linearized model, while R2,
RMSE and MAE are computed on the original response scale.
"""

from __future__ import annotations

import math

import numpy as np

from . import diagnostics, stats
from .data import build_dataset
from .models import (
    AnalysisError,
    ComparisonRow,
    FitResult,
    ModelKind,
    ModelSpec,
    Prediction,
)

MAX_DEGREE = 10
_LOG_RESPONSE = (ModelKind.EXPONENTIAL, ModelKind.POWER)
_LOG_PREDICTOR = (ModelKind.LOGARITHMIC, ModelKind.POWER)


class RegressionError(AnalysisError):
    """The data cannot support the requested model."""


# --- design matrix ----------------------------------------------------------


def _design(spec: ModelSpec, x: np.ndarray, center: float, scale: float) -> np.ndarray:
    kind = spec.kind
    ones = np.ones(x.shape[0])
    if kind in (ModelKind.LINEAR, ModelKind.EXPONENTIAL):
        return np.column_stack([ones, x[:, 0]])
    if kind is ModelKind.POLYNOMIAL:
        u = (x[:, 0] - center) / scale
        return np.column_stack([u**j for j in range(spec.degree + 1)])
    if kind in _LOG_PREDICTOR:
        return np.column_stack([ones, np.log(x[:, 0])])
    return np.column_stack([ones] + [x[:, j] for j in range(x.shape[1])])


def _n_params(spec: ModelSpec, k: int) -> int:
    if spec.kind is ModelKind.POLYNOMIAL:
        return spec.degree + 1
    if spec.kind is ModelKind.MULTIPLE:
        return k + 1
    return 2


def _check_domain(kind: ModelKind, x: np.ndarray, y: np.ndarray | None) -> None:
    if kind in _LOG_PREDICTOR and np.any(x <= 0):
        raise RegressionError(f"{kind.label} regression needs every predictor value > 0.")
    if y is not None and kind in _LOG_RESPONSE and np.any(y <= 0):
        raise RegressionError(f"{kind.label} regression needs every response value > 0.")


def _ols(X: np.ndarray, y: np.ndarray):
    n, p = X.shape
    if np.linalg.matrix_rank(X) < p:
        raise RegressionError(
            "The predictors are collinear, or have too few distinct values for this model."
        )
    q, r = np.linalg.qr(X)
    beta = np.linalg.solve(r, q.T @ y)
    resid = y - X @ beta
    sse = float(resid @ resid)
    sigma2 = sse / (n - p)
    r_inv = np.linalg.inv(r)
    cov = sigma2 * (r_inv @ r_inv.T)
    return beta, cov, sse, sigma2, q, r_inv


def _poly_to_raw(beta: np.ndarray, cov: np.ndarray, center: float, scale: float):
    """Convert coefficients of a centered/scaled polynomial to raw-x terms."""
    p = beta.size
    t = np.zeros((p, p))
    for j in range(p):
        for k in range(j + 1):
            t[k, j] = math.comb(j, k) * scale ** (-k) * (-center / scale) ** (j - k)
    return t @ beta, t @ cov @ t.T


# --- text helpers ---------------------------------------------------------------


def _join_terms(terms: list[tuple[float, str | None]]) -> str:
    out = ""
    for i, (value, label) in enumerate(terms):
        body = f"{abs(value):.5g}" + (f" * {label}" if label else "")
        if i == 0:
            out += ("-" if value < 0 else "") + body
        else:
            out += (" - " if value < 0 else " + ") + body
    return out


def _equation(spec: ModelSpec, coef: np.ndarray) -> str:
    y, xs, kind = spec.y_col, spec.x_cols, spec.kind
    if kind is ModelKind.POLYNOMIAL:
        terms = [(float(coef[0]), None), (float(coef[1]), xs[0])]
        terms += [(float(c), f"{xs[0]}^{j}") for j, c in enumerate(coef[2:], start=2)]
        return f"{y} = {_join_terms(terms)}"
    if kind is ModelKind.EXPONENTIAL:
        return f"{y} = {math.exp(coef[0]):.5g} * exp({coef[1]:.5g} * {xs[0]})"
    if kind is ModelKind.POWER:
        return f"{y} = {math.exp(coef[0]):.5g} * {xs[0]}^{coef[1]:.5g}"
    if kind is ModelKind.LOGARITHMIC:
        terms = [(float(coef[0]), None), (float(coef[1]), f"ln({xs[0]})")]
        return f"{y} = {_join_terms(terms)}"
    terms = [(float(coef[0]), None)] + [
        (float(c), name) for c, name in zip(coef[1:], xs)
    ]
    return f"{y} = {_join_terms(terms)}"


def _term_names(spec: ModelSpec) -> list[str]:
    xs, kind = spec.x_cols, spec.kind
    if kind is ModelKind.POLYNOMIAL:
        return ["intercept", xs[0]] + [f"{xs[0]}^{j}" for j in range(2, spec.degree + 1)]
    if kind in _LOG_RESPONSE:
        return ["ln(a)", "b"]
    if kind is ModelKind.LOGARITHMIC:
        return ["intercept", f"ln({xs[0]})"]
    return ["intercept", *xs]


# --- fitting ----------------------------------------------------------------


def fit(
    x: np.ndarray,
    y: np.ndarray,
    spec: ModelSpec,
    level: float = 0.95,
    n_dropped: int = 0,
    row_index: np.ndarray | None = None,
    x_excluded: np.ndarray | None = None,
    y_excluded: np.ndarray | None = None,
    rows_excluded: np.ndarray | None = None,
) -> FitResult:
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    y = np.asarray(y, dtype=float)
    kind, k, n = spec.kind, x.shape[1], y.size

    if kind is not ModelKind.MULTIPLE and k != 1:
        raise RegressionError(f"{kind.label} regression needs exactly one predictor.")
    if kind is ModelKind.POLYNOMIAL and not 1 <= spec.degree <= MAX_DEGREE:
        raise RegressionError(f"Polynomial degree must be between 1 and {MAX_DEGREE}.")
    _check_domain(kind, x, y)

    center, scale = 0.0, 1.0
    if kind is ModelKind.POLYNOMIAL:
        center, scale = float(x[:, 0].mean()), float(x[:, 0].std())
        if scale == 0.0:
            raise RegressionError("The predictor has no variation (all values equal).")

    p = _n_params(spec, k)
    if n <= p:
        raise RegressionError(
            f"This model has {p} parameters and needs more than {p} observations; got {n}."
        )

    transformed = kind in _LOG_RESPONSE
    design = _design(spec, x, center, scale)
    y_fit = np.log(y) if transformed else y
    beta, cov, sse_fit, sigma2, q, r_inv = _ols(design, y_fit)
    dof = n - p

    fitted_fit = design @ beta
    fitted = np.exp(fitted_fit) if transformed else fitted_fit
    residuals = y - fitted
    resid_fit = y_fit - fitted_fit

    inf = diagnostics.influence(q, resid_fit, p)
    bp_stat, bp_p, bp_df = diagnostics.breusch_pagan(design, resid_fit)
    cov_source = (
        diagnostics.hc3_covariance(q, r_inv, resid_fit, inf.leverage) if spec.robust else cov
    )

    if kind is ModelKind.POLYNOMIAL:
        coef, cov_report = _poly_to_raw(beta, cov_source, center, scale)
    else:
        coef, cov_report = beta, cov_source
    std_err = np.sqrt(np.clip(np.diag(cov_report), 0.0, None))
    with np.errstate(divide="ignore", invalid="ignore"):
        t_stat = coef / std_err
    p_values = np.array([stats.t_sf_two_sided(float(t), dof) for t in t_stat])
    t_crit = stats.t_ppf(0.5 + level / 2.0, dof)

    sse = float(residuals @ residuals)
    sst = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - sse / sst if sst > 0 else math.nan
    adj_r2 = 1.0 - (1.0 - r2) * (n - 1) / (n - p) if sst > 0 else math.nan

    sst_fit = float(np.sum((y_fit - y_fit.mean()) ** 2))
    if sse_fit == 0.0:
        f_stat, f_p = math.inf, 0.0
    elif sst_fit == 0.0:
        f_stat, f_p = math.nan, math.nan
    else:
        f_stat = ((sst_fit - sse_fit) / (p - 1)) / (sse_fit / dof)
        f_p = stats.f_sf(f_stat, p - 1, dof)

    jb_stat, jb_p = stats.jarque_bera(residuals)
    qq_theory, qq_sample = stats.qq_points(residuals)

    notes: list[str] = []
    if transformed:
        notes.append(
            "Coefficient statistics, the F-test and the residual standard error describe "
            "the log-linearized model; R2, RMSE and MAE use the original response scale."
        )
        notes.append("Fitted values are back-transformed medians (no bias correction).")
    if spec.robust:
        notes.append(
            "Standard errors, t-tests and confidence intervals use HC3 robust covariance; "
            "the F-test and prediction intervals still assume constant variance."
        )
    if dof < 5:
        notes.append(f"Only {dof} residual degrees of freedom: estimates are unstable.")

    return FitResult(
        spec=spec,
        n=n,
        n_dropped=n_dropped,
        level=level,
        x=x,
        y=y,
        fitted=fitted,
        residuals=residuals,
        term_names=_term_names(spec),
        coef=coef,
        std_err=std_err,
        t_stat=t_stat,
        p_values=p_values,
        ci_low=coef - t_crit * std_err,
        ci_high=coef + t_crit * std_err,
        r2=r2,
        adj_r2=adj_r2,
        rmse=math.sqrt(sse / n),
        mae=float(np.mean(np.abs(residuals))),
        sigma=math.sqrt(sigma2),
        dof=dof,
        f_stat=f_stat,
        f_p=f_p,
        durbin_watson=stats.durbin_watson(residuals),
        jb_stat=jb_stat,
        jb_p=jb_p,
        equation=_equation(spec, coef),
        row_index=np.arange(n) if row_index is None else np.asarray(row_index),
        x_excluded=np.empty((0, k)) if x_excluded is None else np.asarray(x_excluded, dtype=float),
        y_excluded=np.empty(0) if y_excluded is None else np.asarray(y_excluded, dtype=float),
        rows_excluded=np.empty(0, dtype=int) if rows_excluded is None else np.asarray(rows_excluded),
        leverage=inf.leverage,
        studentized=inf.studentized,
        cooks=inf.cooks,
        flags=diagnostics.flags(inf, n, p),
        bp_stat=bp_stat,
        bp_p=bp_p,
        bp_df=bp_df,
        qq_theory=qq_theory,
        qq_sample=qq_sample,
        beta_fit=beta,
        cov_fit=cov,
        sigma2=sigma2,
        center=center,
        scale=scale,
        notes=notes,
    )


# --- prediction -------------------------------------------------------------


def predict(
    result: FitResult,
    x_new: np.ndarray,
    level: float | None = None,
    with_intervals: bool = True,
) -> Prediction:
    level = result.level if level is None else level
    x_new = np.asarray(x_new, dtype=float)
    if x_new.ndim == 1:
        x_new = x_new[:, None]
    if x_new.shape[1] != result.x.shape[1]:
        raise RegressionError("Wrong number of predictor values.")
    _check_domain(result.spec.kind, x_new, None)

    design = _design(result.spec, x_new, result.center, result.scale)
    mean = design @ result.beta_fit
    inverse = np.exp if result.spec.kind in _LOG_RESPONSE else (lambda v: v)

    if with_intervals:
        var_mean = np.einsum("ij,jk,ik->i", design, result.cov_fit, design)
        t_crit = stats.t_ppf(0.5 + level / 2.0, result.dof)
        se_mean = np.sqrt(np.clip(var_mean, 0.0, None))
        se_pred = np.sqrt(np.clip(var_mean + result.sigma2, 0.0, None))
        ci_low, ci_high = mean - t_crit * se_mean, mean + t_crit * se_mean
        pi_low, pi_high = mean - t_crit * se_pred, mean + t_crit * se_pred
    else:
        ci_low = ci_high = pi_low = pi_high = np.full(mean.shape, np.nan)

    outside = (x_new < result.x.min(axis=0)) | (x_new > result.x.max(axis=0))
    return Prediction(
        x=x_new,
        yhat=inverse(mean),
        ci_low=inverse(ci_low),
        ci_high=inverse(ci_high),
        pi_low=inverse(pi_low),
        pi_high=inverse(pi_high),
        extrapolated=outside.any(axis=1),
        level=level,
    )


def curve_grid(result: FitResult, n: int = 300) -> np.ndarray:
    """Evenly spaced predictor values spanning the data (single predictor)."""
    column = result.x[:, 0]
    return np.linspace(float(column.min()), float(column.max()), n)


def excluded_fitted(result: FitResult) -> np.ndarray:
    """Model values at the excluded points (NaN where the model is undefined)."""
    xe = result.x_excluded
    out = np.full(xe.shape[0], np.nan)
    if xe.shape[0] == 0:
        return out
    ok = np.ones(xe.shape[0], dtype=bool)
    if result.spec.kind in _LOG_PREDICTOR:
        ok = xe[:, 0] > 0
    if ok.any():
        design = _design(result.spec, xe[ok], result.center, result.scale)
        mean = design @ result.beta_fit
        out[ok] = np.exp(mean) if result.spec.kind in _LOG_RESPONSE else mean
    return out


# --- model comparison -------------------------------------------------------

_CANDIDATES = (
    (ModelKind.LINEAR, 1),
    (ModelKind.POLYNOMIAL, 2),
    (ModelKind.POLYNOMIAL, 3),
    (ModelKind.EXPONENTIAL, 1),
    (ModelKind.LOGARITHMIC, 1),
    (ModelKind.POWER, 1),
)


def _cv_rmse(x: np.ndarray, y: np.ndarray, spec: ModelSpec, folds: int) -> float:
    n = y.size
    k = min(folds, n)
    if k < 2:
        return math.nan
    order = np.random.default_rng(0).permutation(n)
    squared: list[np.ndarray] = []
    for part in np.array_split(order, k):
        train = np.setdiff1d(order, part)
        try:
            model = fit(x[train], y[train], spec)
            pred = predict(model, x[part], with_intervals=False).yhat
        except AnalysisError:
            return math.nan
        squared.append((y[part] - pred) ** 2)
    return math.sqrt(float(np.mean(np.concatenate(squared))))


def compare_models(
    x: np.ndarray, y: np.ndarray, x_name: str, y_name: str, folds: int = 5
) -> list[ComparisonRow]:
    """Fit every single-predictor model and rank by cross-validated RMSE."""
    rows: list[ComparisonRow] = []
    for kind, degree in _CANDIDATES:
        spec = ModelSpec(kind, y_name, (x_name,), degree)
        try:
            result = fit(x, y, spec)
        except AnalysisError as exc:
            rows.append(ComparisonRow(spec.describe(), math.nan, math.nan, math.nan, math.nan, str(exc)))
            continue
        cv = _cv_rmse(x, y, spec, folds)
        rows.append(ComparisonRow(spec.describe(), result.r2, result.adj_r2, result.rmse, cv))

    def key(row: ComparisonRow) -> tuple[int, float]:
        if not math.isnan(row.cv_rmse):
            return (0, row.cv_rmse)
        if not math.isnan(row.rmse):
            return (1, row.rmse)
        return (2, 0.0)

    return sorted(rows, key=key)


# --- entry points used by the UI (run on a worker thread) -------------------


def _split_excluded(selection, excluded: frozenset[int]):
    mask = np.isin(selection.rows, list(excluded)) if excluded else np.zeros(selection.rows.size, bool)
    return mask


def analyze(headers: list[str], rows: list[list[str]], spec: ModelSpec) -> FitResult:
    selection = build_dataset(headers, rows).extract(spec.x_cols, spec.y_col)
    gone = _split_excluded(selection, spec.excluded)
    keep = ~gone
    return fit(
        selection.x[keep],
        selection.y[keep],
        spec,
        n_dropped=selection.n_dropped,
        row_index=selection.rows[keep],
        x_excluded=selection.x[gone],
        y_excluded=selection.y[gone],
        rows_excluded=selection.rows[gone],
    )


def analyze_compare(
    headers: list[str],
    rows: list[list[str]],
    x_col: str,
    y_col: str,
    excluded: frozenset[int] = frozenset(),
) -> tuple[list[ComparisonRow], int]:
    selection = build_dataset(headers, rows).extract((x_col,), y_col)
    keep = ~_split_excluded(selection, excluded)
    x, y = selection.x[keep], selection.y[keep]
    return compare_models(x, y, x_col, y_col), int(y.size)
