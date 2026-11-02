"""Descriptive statistics for numeric and categorical columns. No Qt imports."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from core.data_loader import coerce_numeric
from core.models import CategoricalSummary, ColumnSummary


def summarize_numeric(series: pd.Series, name: str) -> ColumnSummary:
    values = coerce_numeric(series)
    missing = int(values.isna().sum())
    clean = values.dropna().to_numpy(dtype=float)
    n = len(clean)

    if n == 0:
        zero = 0.0
        return ColumnSummary(
            name=name, count=0, missing=missing, mean=zero, median=zero,
            mode=None, std_dev=zero, variance=zero, minimum=zero, maximum=zero,
            range_=zero, q1=zero, q3=zero, iqr=zero, skewness=zero,
            kurtosis=zero, sem=zero, ci_95_low=zero, ci_95_high=zero,
        )

    mean = float(np.mean(clean))
    median = float(np.median(clean))
    std_dev = float(np.std(clean, ddof=1)) if n > 1 else 0.0
    variance = float(np.var(clean, ddof=1)) if n > 1 else 0.0
    minimum = float(np.min(clean))
    maximum = float(np.max(clean))
    q1 = float(np.percentile(clean, 25))
    q3 = float(np.percentile(clean, 75))

    mode_result = sp_stats.mode(clean, keepdims=True)
    mode_val = float(mode_result.mode[0]) if mode_result.count[0] > 0 else None

    skewness = float(sp_stats.skew(clean)) if n > 2 else 0.0
    kurtosis = float(sp_stats.kurtosis(clean)) if n > 3 else 0.0
    sem = float(sp_stats.sem(clean)) if n > 1 else 0.0

    if n > 1:
        ci = sp_stats.t.interval(0.95, df=n - 1, loc=mean, scale=sem)
        ci_low, ci_high = float(ci[0]), float(ci[1])
    else:
        ci_low, ci_high = mean, mean

    return ColumnSummary(
        name=name,
        count=n,
        missing=missing,
        mean=mean,
        median=median,
        mode=mode_val,
        std_dev=std_dev,
        variance=variance,
        minimum=minimum,
        maximum=maximum,
        range_=maximum - minimum,
        q1=q1,
        q3=q3,
        iqr=q3 - q1,
        skewness=skewness,
        kurtosis=kurtosis,
        sem=sem,
        ci_95_low=ci_low,
        ci_95_high=ci_high,
    )


def summarize_categorical(series: pd.Series, name: str) -> CategoricalSummary:
    missing = int(series.isna().sum())
    clean = series.dropna().astype(str)
    n = len(clean)
    counts = clean.value_counts()

    top_value = str(counts.index[0]) if len(counts) > 0 else None
    top_freq = int(counts.iloc[0]) if len(counts) > 0 else 0

    return CategoricalSummary(
        name=name,
        count=n,
        missing=missing,
        unique=int(clean.nunique()),
        top_value=top_value,
        top_frequency=top_freq,
        frequencies=counts.head(50).to_dict(),
    )


def detect_outliers_iqr(series: pd.Series) -> tuple[np.ndarray, float, float]:
    """Return (outlier values, lower fence, upper fence) using the 1.5*IQR rule."""
    values = coerce_numeric(series).dropna().to_numpy(dtype=float)
    if len(values) == 0:
        return np.array([]), 0.0, 0.0
    q1, q3 = np.percentile(values, [25, 75])
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outliers = values[(values < lower) | (values > upper)]
    return outliers, float(lower), float(upper)


def histogram_bins(series: pd.Series, bin_count: int = 20) -> tuple[np.ndarray, np.ndarray]:
    """Return (counts, bin_edges) for a numeric column, using Sturges' rule
    as the default bin count if bin_count is not explicitly overridden."""
    values = coerce_numeric(series).dropna().to_numpy(dtype=float)
    if len(values) == 0:
        return np.array([]), np.array([])
    counts, edges = np.histogram(values, bins=bin_count)
    return counts, edges
