"""Plain data models for StatLab. No PyQt6.QtWidgets imports here."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ColumnKind(Enum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    UNKNOWN = "unknown"


@dataclass
class ColumnSummary:
    """Descriptive-statistics summary for a single numeric column."""

    name: str
    count: int
    missing: int
    mean: float
    median: float
    mode: float | None
    std_dev: float
    variance: float
    minimum: float
    maximum: float
    range_: float
    q1: float
    q3: float
    iqr: float
    skewness: float
    kurtosis: float
    sem: float  # standard error of the mean
    ci_95_low: float
    ci_95_high: float


@dataclass
class CategoricalSummary:
    """Frequency summary for a non-numeric column."""

    name: str
    count: int
    missing: int
    unique: int
    top_value: str | None
    top_frequency: int
    frequencies: dict[str, int] = field(default_factory=dict)


@dataclass
class Dataset:
    """Wraps a loaded table plus the detected kind of each column."""

    source_path: str
    row_count: int
    column_names: list[str]
    column_kinds: dict[str, ColumnKind]


@dataclass
class CorrelationResult:
    col_x: str
    col_y: str
    pearson_r: float
    pearson_p: float
    spearman_r: float
    spearman_p: float
    n: int


@dataclass
class TTestResult:
    kind: str  # "one_sample", "two_sample_ind", "paired"
    statistic: float
    p_value: float
    df: float
    mean_diff: float
    ci_95_low: float
    ci_95_high: float


@dataclass
class ChiSquareResult:
    statistic: float
    p_value: float
    df: int
    expected_valid: bool  # False if any expected count < 5


@dataclass
class AnovaResult:
    statistic: float
    p_value: float
    df_between: int
    df_within: int
    group_names: list[str]


@dataclass
class RegressionResult:
    slope: float
    intercept: float
    r_value: float
    r_squared: float
    p_value: float
    std_err: float


@dataclass
class DistributionQuery:
    distribution: str  # "normal", "binomial", "poisson", "uniform", "exponential"
    params: dict[str, float]


@dataclass
class DistributionPoint:
    x: list[float]
    pdf_or_pmf: list[float]
    cdf: list[float]
