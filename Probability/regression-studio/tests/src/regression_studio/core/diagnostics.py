"""Influence measures and heteroscedasticity tests. No Qt imports.

All quantities refer to the fitted (possibly log-transformed) scale, i.e.
to the ordinary least squares problem that was actually solved.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import stats

# Rules of thumb used to flag points.
OUTLIER_LIMIT = 3.0  # |externally studentized residual|


@dataclass
class Influence:
    leverage: np.ndarray
    studentized: np.ndarray  # externally studentized residuals
    cooks: np.ndarray


def influence(q: np.ndarray, resid: np.ndarray, p: int) -> Influence:
    """Leverage, studentized residuals and Cook's distance.

    `q` is the thin Q factor of the design matrix, so leverage is the row sum
    of squares of Q (the diagonal of the hat matrix).
    """
    n = resid.size
    dof = n - p
    leverage = np.sum(q**2, axis=1)
    room = np.clip(1.0 - leverage, 1e-12, None)
    sse = float(resid @ resid)
    s2 = sse / dof
    with np.errstate(divide="ignore", invalid="ignore"):
        internal = resid / np.sqrt(s2 * room)
        # Leave-one-out variance gives the externally studentized residual.
        s2_loo = (sse - resid**2 / room) / (dof - 1) if dof > 1 else np.full(n, np.nan)
        external = resid / np.sqrt(np.clip(s2_loo, 0.0, None) * room)
        cooks = internal**2 / p * leverage / room
    return Influence(leverage, external, cooks)


def flags(inf: Influence, n: int, p: int) -> list[list[str]]:
    """Per-point flag labels based on common rules of thumb."""
    result: list[list[str]] = []
    for h, t, d in zip(inf.leverage, inf.studentized, inf.cooks):
        labels = []
        if h > 2.0 * p / n:
            labels.append("leverage")
        if abs(t) > OUTLIER_LIMIT:
            labels.append("outlier")
        if d > 4.0 / n:
            labels.append("influential")
        result.append(labels)
    return result


def hc3_covariance(q: np.ndarray, r_inv: np.ndarray, resid: np.ndarray, leverage: np.ndarray) -> np.ndarray:
    """HC3 heteroscedasticity-robust covariance of the OLS coefficients."""
    room = np.clip(1.0 - leverage, 1e-12, None)
    a = q @ r_inv.T  # X (X'X)^-1 for X = QR
    w = (resid / room) ** 2
    return a.T @ (a * w[:, None])


def breusch_pagan(design: np.ndarray, resid: np.ndarray) -> tuple[float, float, int]:
    """Breusch-Pagan test (Koenker's studentized form).

    Returns (LM statistic, p-value, degrees of freedom). The auxiliary
    regression of squared residuals on the design needs at least one non-constant
    column, otherwise the test is undefined.
    """
    n, p = design.shape
    dof = p - 1
    if dof < 1 or n <= p:
        return float("nan"), float("nan"), max(dof, 0)
    e2 = resid**2
    centered = e2 - e2.mean()
    sst = float(centered @ centered)
    if sst == 0.0:
        return float("nan"), float("nan"), dof
    coef, *_ = np.linalg.lstsq(design, e2, rcond=None)
    ssr = float(np.sum((design @ coef - e2.mean()) ** 2))
    lm = n * ssr / sst
    return lm, stats.chi2_sf(lm, dof), dof
