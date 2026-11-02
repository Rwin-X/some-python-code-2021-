"""Inferential statistics: correlation, hypothesis tests, regression.
No Qt imports."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from core.data_loader import coerce_numeric
from core.models import (
    AnovaResult,
    ChiSquareResult,
    CorrelationResult,
    RegressionResult,
    TTestResult,
)


def _paired_clean(a: pd.Series, b: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    df = pd.DataFrame({"a": coerce_numeric(a), "b": coerce_numeric(b)}).dropna()
    return df["a"].to_numpy(dtype=float), df["b"].to_numpy(dtype=float)


def correlation(series_x: pd.Series, series_y: pd.Series, name_x: str, name_y: str) -> CorrelationResult:
    x, y = _paired_clean(series_x, series_y)
    n = len(x)
    if n < 3:
        return CorrelationResult(col_x=name_x, col_y=name_y, pearson_r=0.0, pearson_p=1.0,
                                  spearman_r=0.0, spearman_p=1.0, n=n)
    pearson_r, pearson_p = sp_stats.pearsonr(x, y)
    spearman_r, spearman_p = sp_stats.spearmanr(x, y)
    return CorrelationResult(
        col_x=name_x, col_y=name_y,
        pearson_r=float(pearson_r), pearson_p=float(pearson_p),
        spearman_r=float(spearman_r), spearman_p=float(spearman_p),
        n=n,
    )


def correlation_matrix(df: pd.DataFrame, numeric_cols: list[str]) -> pd.DataFrame:
    coerced = df[numeric_cols].apply(coerce_numeric)
    return coerced.corr(method="pearson")


def linear_regression(series_x: pd.Series, series_y: pd.Series) -> RegressionResult:
    x, y = _paired_clean(series_x, series_y)
    result = sp_stats.linregress(x, y)
    return RegressionResult(
        slope=float(result.slope),
        intercept=float(result.intercept),
        r_value=float(result.rvalue),
        r_squared=float(result.rvalue) ** 2,
        p_value=float(result.pvalue),
        std_err=float(result.stderr),
    )


def one_sample_ttest(series: pd.Series, popmean: float) -> TTestResult:
    values = coerce_numeric(series).dropna().to_numpy(dtype=float)
    n = len(values)
    stat, p = sp_stats.ttest_1samp(values, popmean)
    mean_diff = float(np.mean(values) - popmean)
    sem = sp_stats.sem(values)
    ci = sp_stats.t.interval(0.95, df=n - 1, loc=np.mean(values), scale=sem)
    return TTestResult(
        kind="one_sample", statistic=float(stat), p_value=float(p), df=float(n - 1),
        mean_diff=mean_diff, ci_95_low=float(ci[0]), ci_95_high=float(ci[1]),
    )


def two_sample_ttest(series_a: pd.Series, series_b: pd.Series, equal_var: bool = False) -> TTestResult:
    a = coerce_numeric(series_a).dropna().to_numpy(dtype=float)
    b = coerce_numeric(series_b).dropna().to_numpy(dtype=float)
    stat, p = sp_stats.ttest_ind(a, b, equal_var=equal_var)

    mean_diff = float(np.mean(a) - np.mean(b))
    na, nb = len(a), len(b)
    va, vb = np.var(a, ddof=1), np.var(b, ddof=1)

    if equal_var:
        df = na + nb - 2
        pooled_var = ((na - 1) * va + (nb - 1) * vb) / df
        se = np.sqrt(pooled_var * (1 / na + 1 / nb))
    else:
        se = np.sqrt(va / na + vb / nb)
        df = (va / na + vb / nb) ** 2 / (
            (va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1)
        )

    ci = sp_stats.t.interval(0.95, df=df, loc=mean_diff, scale=se)
    return TTestResult(
        kind="two_sample_ind", statistic=float(stat), p_value=float(p), df=float(df),
        mean_diff=mean_diff, ci_95_low=float(ci[0]), ci_95_high=float(ci[1]),
    )


def paired_ttest(series_a: pd.Series, series_b: pd.Series) -> TTestResult:
    a, b = _paired_clean(series_a, series_b)
    diffs = a - b
    n = len(diffs)
    stat, p = sp_stats.ttest_rel(a, b)
    mean_diff = float(np.mean(diffs))
    sem = sp_stats.sem(diffs)
    ci = sp_stats.t.interval(0.95, df=n - 1, loc=mean_diff, scale=sem)
    return TTestResult(
        kind="paired", statistic=float(stat), p_value=float(p), df=float(n - 1),
        mean_diff=mean_diff, ci_95_low=float(ci[0]), ci_95_high=float(ci[1]),
    )


def chi_square_independence(df: pd.DataFrame, col_a: str, col_b: str) -> ChiSquareResult:
    contingency = pd.crosstab(df[col_a].astype(str), df[col_b].astype(str))
    stat, p, dof, expected = sp_stats.chi2_contingency(contingency)
    expected_valid = bool(np.all(expected >= 5))
    return ChiSquareResult(statistic=float(stat), p_value=float(p), df=int(dof), expected_valid=expected_valid)


def one_way_anova(df: pd.DataFrame, value_col: str, group_col: str) -> AnovaResult:
    groups_df = pd.DataFrame({
        "value": coerce_numeric(df[value_col]),
        "group": df[group_col].astype(str),
    }).dropna()

    group_names = sorted(groups_df["group"].unique().tolist())
    samples = [groups_df.loc[groups_df["group"] == g, "value"].to_numpy(dtype=float) for g in group_names]
    samples = [s for s in samples if len(s) > 0]

    stat, p = sp_stats.f_oneway(*samples)

    k = len(samples)
    n_total = sum(len(s) for s in samples)
    df_between = k - 1
    df_within = n_total - k

    return AnovaResult(
        statistic=float(stat), p_value=float(p),
        df_between=df_between, df_within=df_within,
        group_names=group_names,
    )


def interpret_p_value(p: float, alpha: float = 0.05) -> str:
    if p < alpha:
        return f"p = {p:.4g} < alpha ({alpha}): reject the null hypothesis"
    return f"p = {p:.4g} >= alpha ({alpha}): fail to reject the null hypothesis"
