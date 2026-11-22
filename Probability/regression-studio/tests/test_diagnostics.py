"""Influence measures, Breusch-Pagan and HC3 checked against direct numpy formulas."""

import math

import numpy as np
import pytest

from regression_studio.core import data, engine
from regression_studio.core.models import ModelKind, ModelSpec

sps = pytest.importorskip("scipy.stats")


@pytest.fixture
def hetero():
    rng = np.random.default_rng(11)
    x = np.linspace(1, 12, 45)
    y = 2 + 1.1 * x + rng.normal(0, 0.3 + 0.15 * x)
    y[7] += 9
    return x, y


def design(x):
    return np.column_stack([np.ones_like(x), x])


def fit_linear(x, y, **kw):
    return engine.fit(x, y, ModelSpec(ModelKind.LINEAR, "y", ("x",), **kw))


def test_leverage_is_hat_matrix_diagonal(hetero):
    x, y = hetero
    X = design(x)
    hat = np.diag(X @ np.linalg.inv(X.T @ X) @ X.T)
    r = fit_linear(x, y)
    assert r.leverage == pytest.approx(hat)
    assert r.leverage.sum() == pytest.approx(2.0)  # trace of hat matrix == p


def test_studentized_residuals_match_leave_one_out(hetero):
    x, y = hetero
    r = fit_linear(x, y)
    n = x.size
    strict = np.empty(n)
    for i in range(n):
        keep = np.arange(n) != i
        Xk = design(x[keep])
        beta = np.linalg.lstsq(Xk, y[keep], rcond=None)[0]
        s_i = math.sqrt(np.sum((y[keep] - Xk @ beta) ** 2) / (n - 1 - 2))
        # t_i = e_i / (s_(i) * sqrt(1 - h_i)) with s_(i) from the refit without point i
        strict[i] = r.residuals[i] / (s_i * math.sqrt(1 - r.leverage[i]))
    assert r.studentized == pytest.approx(strict, rel=1e-9)


def test_cooks_distance_formula(hetero):
    x, y = hetero
    r = fit_linear(x, y)
    p, s2 = 2, r.sigma**2
    expected = r.residuals**2 / (p * s2) * r.leverage / (1 - r.leverage) ** 2
    assert r.cooks == pytest.approx(expected)


def test_planted_outlier_is_flagged(hetero):
    x, y = hetero
    r = fit_linear(x, y)
    assert r.cooks.argmax() == 7
    assert "outlier" in r.flags[7]


def test_breusch_pagan_matches_manual_koenker(hetero):
    x, y = hetero
    r = fit_linear(x, y)
    e2 = r.residuals**2
    X = design(x)
    fitted = X @ np.linalg.lstsq(X, e2, rcond=None)[0]
    r2_aux = 1 - np.sum((e2 - fitted) ** 2) / np.sum((e2 - e2.mean()) ** 2)
    lm = x.size * r2_aux
    assert r.bp_stat == pytest.approx(lm)
    assert r.bp_p == pytest.approx(float(sps.chi2.sf(lm, 1)), rel=1e-8)
    assert r.bp_df == 1


def test_breusch_pagan_detects_heteroscedasticity():
    rng = np.random.default_rng(2)
    x = np.linspace(1, 10, 400)
    het = fit_linear(x, 1 + x + rng.normal(0, 0.2 * x**1.5))
    homo = fit_linear(x, 1 + x + rng.normal(0, 1.0, x.size))
    assert het.bp_p < 0.001
    assert homo.bp_p > 0.01


def test_hc3_matches_explicit_sandwich(hetero):
    x, y = hetero
    X = design(x)
    r = fit_linear(x, y, robust=True)
    bread = np.linalg.inv(X.T @ X)
    h = np.diag(X @ bread @ X.T)
    e = y - X @ (bread @ X.T @ y)
    meat = X.T @ np.diag(e**2 / (1 - h) ** 2) @ X
    sandwich = bread @ meat @ bread
    assert r.std_err == pytest.approx(np.sqrt(np.diag(sandwich)))
    classic = fit_linear(x, y)
    assert classic.coef == pytest.approx(r.coef)  # estimates unchanged
    assert not np.allclose(classic.std_err, r.std_err)
    assert any("HC3" in note for note in r.notes)


def test_hc3_polynomial_uses_raw_basis():
    rng = np.random.default_rng(8)
    x = np.linspace(2000, 2020, 30)
    y = 1 + 0.2 * (x - 2010) ** 2 + rng.normal(0, 0.5 + 0.05 * (x - 2000), x.size)
    r = engine.fit(x, y, ModelSpec(ModelKind.POLYNOMIAL, "y", ("x",), 2, robust=True))
    X = np.column_stack([np.ones_like(x), x - 2010, (x - 2010) ** 2])  # centered basis, easy to invert
    bread = np.linalg.inv(X.T @ X)
    h = np.diag(X @ bread @ X.T)
    e = y - X @ (bread @ X.T @ y)
    cov_c = bread @ (X.T @ np.diag(e**2 / (1 - h) ** 2) @ X) @ bread
    # raw coefficient of x^2 equals the centered one, so their standard errors must match
    assert r.std_err[2] == pytest.approx(math.sqrt(cov_c[2, 2]), rel=1e-6)


def test_transformed_model_diagnostics_use_fitted_scale():
    rng = np.random.default_rng(4)
    x = np.linspace(0, 5, 30)
    y = 2 * np.exp(0.4 * x) * np.exp(rng.normal(0, 0.1, x.size))
    r = engine.fit(x, y, ModelSpec(ModelKind.EXPONENTIAL, "y", ("x",)))
    X = design(x)
    hat = np.diag(X @ np.linalg.inv(X.T @ X) @ X.T)
    assert r.leverage == pytest.approx(hat)


def test_analyze_with_exclusions_matches_manual_removal():
    headers, rows = data.sample_table()
    excluded = frozenset({0, 5, 17})
    spec = ModelSpec(ModelKind.LINEAR, "y", ("x",), excluded=excluded)
    r = engine.analyze(headers, rows, spec)
    keep = [i for i in range(len(rows)) if i not in excluded]
    x = np.array([float(rows[i][0]) for i in keep])
    y = np.array([float(rows[i][2]) for i in keep])
    assert r.n == len(keep)
    assert r.coef == pytest.approx(np.polyfit(x, y, 1)[::-1])
    assert sorted(r.rows_excluded.tolist()) == [0, 5, 17]
    assert r.row_index.tolist() == keep
    assert r.y_excluded.size == 3


def test_excluded_fitted_and_domain_guard():
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    y = 2 + np.log(x)
    r = engine.fit(
        x, y, ModelSpec(ModelKind.LOGARITHMIC, "y", ("x",)),
        x_excluded=np.array([[-1.0], [10.0]]), y_excluded=np.array([0.0, 4.0]),
        rows_excluded=np.array([8, 9]),
    )
    vals = engine.excluded_fitted(r)
    assert math.isnan(vals[0])  # ln undefined at x <= 0
    assert vals[1] == pytest.approx(2 + math.log(10.0))
