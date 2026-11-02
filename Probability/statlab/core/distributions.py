"""Probability distribution calculators: PDF/PMF, CDF, quantiles,
random sampling. No Qt imports."""

from __future__ import annotations

import numpy as np
from scipy import stats as sp_stats

from core.models import DistributionPoint

DISTRIBUTION_NAMES = [
    "normal",
    "binomial",
    "poisson",
    "uniform",
    "exponential",
]

# Each entry: display label, parameter specs as (key, label, default, is_integer)
DISTRIBUTION_PARAMS: dict[str, list[tuple[str, str, float, bool]]] = {
    "normal": [("mean", "Mean", 0.0, False), ("std_dev", "Std Dev", 1.0, False)],
    "binomial": [("n", "Trials (n)", 10.0, True), ("p", "Success prob (p)", 0.5, False)],
    "poisson": [("lam", "Rate (lambda)", 3.0, False)],
    "uniform": [("low", "Lower bound", 0.0, False), ("high", "Upper bound", 1.0, False)],
    "exponential": [("rate", "Rate (lambda)", 1.0, False)],
}

DISCRETE_DISTRIBUTIONS = {"binomial", "poisson"}


def _get_frozen(distribution: str, params: dict[str, float]):
    if distribution == "normal":
        return sp_stats.norm(loc=params["mean"], scale=max(params["std_dev"], 1e-9))
    if distribution == "binomial":
        return sp_stats.binom(n=int(params["n"]), p=params["p"])
    if distribution == "poisson":
        return sp_stats.poisson(mu=params["lam"])
    if distribution == "uniform":
        low = params["low"]
        high = params["high"]
        return sp_stats.uniform(loc=low, scale=max(high - low, 1e-9))
    if distribution == "exponential":
        return sp_stats.expon(scale=1.0 / max(params["rate"], 1e-9))
    raise ValueError(f"Unknown distribution: {distribution}")


def compute_curve(distribution: str, params: dict[str, float], points: int = 400) -> DistributionPoint:
    frozen = _get_frozen(distribution, params)

    if distribution in DISCRETE_DISTRIBUTIONS:
        lo = int(frozen.ppf(0.0001))
        hi = int(frozen.ppf(0.9999)) + 1
        lo = max(lo, 0)
        hi = max(hi, lo + 1)
        xs = np.arange(lo, hi + 1)
        pmf = frozen.pmf(xs)
        cdf = frozen.cdf(xs)
        return DistributionPoint(x=xs.tolist(), pdf_or_pmf=pmf.tolist(), cdf=cdf.tolist())

    lo = frozen.ppf(0.001)
    hi = frozen.ppf(0.999)
    if not np.isfinite(lo):
        lo = frozen.mean() - 4 * frozen.std()
    if not np.isfinite(hi):
        hi = frozen.mean() + 4 * frozen.std()
    xs = np.linspace(lo, hi, points)
    pdf = frozen.pdf(xs)
    cdf = frozen.cdf(xs)
    return DistributionPoint(x=xs.tolist(), pdf_or_pmf=pdf.tolist(), cdf=cdf.tolist())


def probability_between(distribution: str, params: dict[str, float], low: float, high: float) -> float:
    frozen = _get_frozen(distribution, params)
    return float(frozen.cdf(high) - frozen.cdf(low))


def probability_at_most(distribution: str, params: dict[str, float], x: float) -> float:
    frozen = _get_frozen(distribution, params)
    return float(frozen.cdf(x))


def probability_at_least(distribution: str, params: dict[str, float], x: float) -> float:
    frozen = _get_frozen(distribution, params)
    return float(1.0 - frozen.cdf(x) + (frozen.pmf(x) if distribution in DISCRETE_DISTRIBUTIONS else 0.0))


def probability_exact(distribution: str, params: dict[str, float], x: float) -> float | None:
    """Only meaningful for discrete distributions; returns None for continuous ones."""
    if distribution not in DISCRETE_DISTRIBUTIONS:
        return None
    frozen = _get_frozen(distribution, params)
    return float(frozen.pmf(x))


def quantile(distribution: str, params: dict[str, float], p: float) -> float:
    frozen = _get_frozen(distribution, params)
    return float(frozen.ppf(p))


def mean_and_variance(distribution: str, params: dict[str, float]) -> tuple[float, float]:
    frozen = _get_frozen(distribution, params)
    return float(frozen.mean()), float(frozen.var())


def sample(distribution: str, params: dict[str, float], size: int, seed: int | None = None) -> np.ndarray:
    frozen = _get_frozen(distribution, params)
    rng = np.random.default_rng(seed)
    return frozen.rvs(size=size, random_state=rng)
