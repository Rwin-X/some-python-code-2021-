"""Plain data structures shared by the regression engine and the UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np


class AnalysisError(Exception):
    """A user-correctable problem with the data or the model settings."""


class ModelKind(Enum):
    LINEAR = "Linear"
    POLYNOMIAL = "Polynomial"
    EXPONENTIAL = "Exponential"
    LOGARITHMIC = "Logarithmic"
    POWER = "Power"
    MULTIPLE = "Multiple linear"

    @property
    def label(self) -> str:
        return self.value


@dataclass(frozen=True)
class ModelSpec:
    kind: ModelKind
    y_col: str
    x_cols: tuple[str, ...]
    degree: int = 2
    robust: bool = False  # use HC3 standard errors in the coefficient table
    excluded: frozenset[int] = frozenset()  # table row indices left out of the fit

    def describe(self) -> str:
        if self.kind is ModelKind.POLYNOMIAL:
            return f"Polynomial (degree {self.degree})"
        return self.kind.label


@dataclass
class FitResult:
    spec: ModelSpec
    n: int
    n_dropped: int
    level: float
    x: np.ndarray  # (n, k) predictors
    y: np.ndarray  # (n,) observed response, original scale
    fitted: np.ndarray  # original scale
    residuals: np.ndarray  # original scale
    term_names: list[str]
    coef: np.ndarray
    std_err: np.ndarray
    t_stat: np.ndarray
    p_values: np.ndarray
    ci_low: np.ndarray
    ci_high: np.ndarray
    r2: float
    adj_r2: float
    rmse: float
    mae: float
    sigma: float  # residual standard error on the fitted scale
    dof: int
    f_stat: float
    f_p: float
    durbin_watson: float
    jb_stat: float
    jb_p: float
    equation: str
    qq_theory: np.ndarray
    qq_sample: np.ndarray
    # Row bookkeeping: table row index (0-based) of every fitted observation.
    row_index: np.ndarray
    x_excluded: np.ndarray  # (m, k) points left out by the user
    y_excluded: np.ndarray
    rows_excluded: np.ndarray
    # Influence diagnostics (fitted scale), one value per fitted observation.
    leverage: np.ndarray
    studentized: np.ndarray
    cooks: np.ndarray
    flags: list[list[str]]
    bp_stat: float
    bp_p: float
    bp_df: int
    # Internals needed for prediction (fitted-scale basis).
    beta_fit: np.ndarray
    cov_fit: np.ndarray
    sigma2: float
    center: float
    scale: float
    notes: list[str] = field(default_factory=list)


@dataclass
class Prediction:
    x: np.ndarray  # (m, k)
    yhat: np.ndarray
    ci_low: np.ndarray  # confidence interval for the mean response
    ci_high: np.ndarray
    pi_low: np.ndarray  # prediction interval for a new observation
    pi_high: np.ndarray
    extrapolated: np.ndarray  # bool, True where x is outside the training range
    level: float


@dataclass
class ComparisonRow:
    label: str
    r2: float
    adj_r2: float
    rmse: float
    cv_rmse: float
    note: str = ""
