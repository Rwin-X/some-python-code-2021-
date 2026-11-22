"""Statistical helpers: t/F tails, quantiles, residual tests.

Implemented with the standard library and numpy only, so the application
does not need scipy at runtime. The test suite cross-checks every function
against scipy.
"""

from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np

_TINY = 1e-300


def _guard(value: float) -> float:
    return value if abs(value) > _TINY else _TINY


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction of the incomplete beta function (modified Lentz)."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 / _guard(1.0 - qab * x / qap)
    h = d
    for m in range(1, 500):
        m2 = 2 * m
        num = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 / _guard(1.0 + num * d)
        c = _guard(1.0 + num / c)
        h *= d * c
        num = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 / _guard(1.0 + num * d)
        c = _guard(1.0 + num / c)
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_front = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log1p(-x)
    )
    front = math.exp(log_front)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def t_sf_two_sided(t: float, dof: float) -> float:
    """Two-sided p-value P(|T| >= |t|) for Student's t with `dof` degrees."""
    if math.isnan(t):
        return math.nan
    if math.isinf(t):
        return 0.0
    return betainc(dof / 2.0, 0.5, dof / (dof + t * t))


def f_sf(f: float, d1: float, d2: float) -> float:
    """Upper-tail probability P(F >= f) of the F distribution."""
    if math.isnan(f):
        return math.nan
    if f <= 0.0:
        return 1.0
    if math.isinf(f):
        return 0.0
    return betainc(d2 / 2.0, d1 / 2.0, d2 / (d2 + d1 * f))


def t_ppf(q: float, dof: float) -> float:
    """Quantile of Student's t for 0.5 < q < 1 (bisection on the tail)."""
    if not 0.5 < q < 1.0:
        raise ValueError("q must be in (0.5, 1)")
    target = 2.0 * (1.0 - q)
    lo, hi = 0.0, 1.0
    while t_sf_two_sided(hi, dof) > target and hi < 1e12:
        hi *= 2.0
    for _ in range(70):
        mid = 0.5 * (lo + hi)
        if t_sf_two_sided(mid, dof) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def qq_points(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Theoretical normal quantiles and sorted sample values."""
    sample = np.sort(np.asarray(values, dtype=float))
    n = sample.size
    probs = (np.arange(1, n + 1) - 0.5) / n
    inv = NormalDist().inv_cdf
    theory = np.array([inv(float(p)) for p in probs])
    return theory, sample


def qq_line(theory: np.ndarray, sample: np.ndarray) -> tuple[float, float]:
    """Reference line through the quartiles of a Q-Q plot (slope, intercept)."""
    if sample.size < 4:
        return float(np.std(sample)), float(np.mean(sample))
    inv = NormalDist().inv_cdf
    q1, q3 = np.percentile(sample, [25, 75])
    t1, t3 = inv(0.25), inv(0.75)
    slope = (q3 - q1) / (t3 - t1)
    return float(slope), float(q1 - slope * t1)


def jarque_bera(values: np.ndarray) -> tuple[float, float]:
    """Jarque-Bera normality statistic and p-value (chi-square, 2 dof)."""
    v = np.asarray(values, dtype=float)
    n = v.size
    if n < 8:
        return math.nan, math.nan
    centered = v - v.mean()
    m2 = float(np.mean(centered**2))
    if m2 == 0.0:
        return math.nan, math.nan
    skew = float(np.mean(centered**3)) / m2**1.5
    kurt = float(np.mean(centered**4)) / m2**2
    stat = n / 6.0 * (skew**2 + (kurt - 3.0) ** 2 / 4.0)
    return stat, math.exp(-stat / 2.0)


def durbin_watson(residuals: np.ndarray) -> float:
    """Durbin-Watson statistic (meaningful when rows are in sequence order)."""
    e = np.asarray(residuals, dtype=float)
    denom = float(e @ e)
    if e.size < 2 or denom == 0.0:
        return math.nan
    return float(np.sum(np.diff(e) ** 2) / denom)


def gammaincc(a: float, x: float) -> float:
    """Regularized upper incomplete gamma function Q(a, x)."""
    if x <= 0.0:
        return 1.0
    log_front = -x + a * math.log(x) - math.lgamma(a)
    if x < a + 1.0:  # series for P(a, x)
        term = total = 1.0 / a
        ap = a
        for _ in range(1000):
            ap += 1.0
            term *= x / ap
            total += term
            if abs(term) < abs(total) * 1e-15:
                break
        return 1.0 - total * math.exp(log_front)
    b = x + 1.0 - a  # continued fraction for Q(a, x), modified Lentz
    c = 1.0 / _TINY
    d = 1.0 / _guard(b)
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = 1.0 / _guard(an * d + b)
        c = _guard(b + an / c)
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return math.exp(log_front) * h


def chi2_sf(x: float, dof: float) -> float:
    """Upper-tail probability P(X >= x) of the chi-square distribution."""
    if math.isnan(x):
        return math.nan
    return gammaincc(dof / 2.0, x / 2.0)
