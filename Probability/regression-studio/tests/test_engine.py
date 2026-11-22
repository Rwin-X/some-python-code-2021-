import math

import numpy as np
import pytest

from regression_studio.core.engine import (
    RegressionError,
    compare_models,
    fit,
    predict,
)
from regression_studio.core.models import ModelKind, ModelSpec
from regression_studio.core.report import build_report

sps = pytest.importorskip("scipy.stats")


def spec(kind, x_cols=("x",), degree=2):
    return ModelSpec(kind, "y", tuple(x_cols), degree)


@pytest.fixture
def linear_data():
    rng = np.random.default_rng(3)
    x = np.linspace(1, 20, 30)
    y = 4.0 + 1.7 * x + rng.normal(0, 1.5, x.size)
    return x, y


def test_linear_matches_scipy(linear_data):
    x, y = linear_data
    r = fit(x, y, spec(ModelKind.LINEAR))
    ref = sps.linregress(x, y)
    assert r.coef[0] == pytest.approx(ref.intercept)
    assert r.coef[1] == pytest.approx(ref.slope)
    assert r.std_err[1] == pytest.approx(ref.stderr)
    assert r.p_values[1] == pytest.approx(ref.pvalue, rel=1e-8)
    assert r.r2 == pytest.approx(ref.rvalue**2)
    assert r.f_p == pytest.approx(ref.pvalue, rel=1e-8)  # one predictor: F-test == t-test
    t_crit = sps.t.ppf(0.975, r.dof)
    assert r.ci_low[1] == pytest.approx(ref.slope - t_crit * ref.stderr)


def test_polynomial_matches_polyfit():
    rng = np.random.default_rng(4)
    x = np.linspace(-3, 5, 40)
    y = 2 - 1.5 * x + 0.8 * x**2 - 0.05 * x**3 + rng.normal(0, 0.4, x.size)
    r = fit(x, y, spec(ModelKind.POLYNOMIAL, degree=3))
    assert r.coef == pytest.approx(np.polyfit(x, y, 3)[::-1], rel=1e-8)


def test_polynomial_is_stable_for_large_offsets():
    # Years as x: a raw Vandermonde matrix would be badly conditioned.
    x = np.arange(2000.0, 2021.0)
    y = 5 + 0.3 * (x - 2010) ** 2 + np.random.default_rng(5).normal(0, 0.2, x.size)
    r = fit(x, y, spec(ModelKind.POLYNOMIAL, degree=2))
    assert r.r2 > 0.999
    pred = predict(r, np.array([2010.0]))
    assert pred.yhat[0] == pytest.approx(5, abs=0.5)


def test_exponential_recovers_parameters():
    x = np.linspace(0, 5, 25)
    y = 2.0 * np.exp(0.4 * x)
    r = fit(x, y, spec(ModelKind.EXPONENTIAL))
    assert math.exp(r.coef[0]) == pytest.approx(2.0)
    assert r.coef[1] == pytest.approx(0.4)
    assert r.r2 == pytest.approx(1.0)
    assert "exp(" in r.equation


def test_power_and_logarithmic():
    x = np.linspace(1, 10, 20)
    power = fit(x, 3.0 * x**1.5, spec(ModelKind.POWER))
    assert math.exp(power.coef[0]) == pytest.approx(3.0)
    assert power.coef[1] == pytest.approx(1.5)
    log = fit(x, 1.0 + 2.0 * np.log(x), spec(ModelKind.LOGARITHMIC))
    assert log.coef == pytest.approx([1.0, 2.0])


def test_multiple_matches_lstsq():
    rng = np.random.default_rng(6)
    X = rng.normal(size=(60, 3))
    y = 1 + X @ np.array([2.0, -1.0, 0.5]) + rng.normal(0, 0.3, 60)
    r = fit(X, y, spec(ModelKind.MULTIPLE, ("a", "b", "c")))
    ref = np.linalg.lstsq(np.column_stack([np.ones(60), X]), y, rcond=None)[0]
    assert r.coef == pytest.approx(ref)


def test_prediction_intervals_match_closed_form(linear_data):
    x, y = linear_data
    r = fit(x, y, spec(ModelKind.LINEAR))
    x0 = 12.5
    pred = predict(r, np.array([x0]))
    n, s = x.size, r.sigma
    sxx = np.sum((x - x.mean()) ** 2)
    t = sps.t.ppf(0.975, n - 2)
    se_mean = s * math.sqrt(1 / n + (x0 - x.mean()) ** 2 / sxx)
    se_pred = s * math.sqrt(1 + 1 / n + (x0 - x.mean()) ** 2 / sxx)
    assert pred.ci_high[0] - pred.yhat[0] == pytest.approx(t * se_mean)
    assert pred.pi_high[0] - pred.yhat[0] == pytest.approx(t * se_pred)
    assert not pred.extrapolated[0]
    assert predict(r, np.array([100.0])).extrapolated[0]


@pytest.mark.parametrize(
    "kind,x,y",
    [
        (ModelKind.EXPONENTIAL, [1, 2, 3, 4], [1, -2, 3, 4]),
        (ModelKind.LOGARITHMIC, [0, 1, 2, 3], [1, 2, 3, 4]),
        (ModelKind.POWER, [1, 2, 3, 4], [0, 2, 3, 4]),
    ],
)
def test_domain_errors(kind, x, y):
    with pytest.raises(RegressionError):
        fit(np.array(x, float), np.array(y, float), spec(kind))


def test_too_few_points_and_collinearity():
    with pytest.raises(RegressionError):
        fit(np.array([1.0, 2.0]), np.array([1.0, 2.0]), spec(ModelKind.LINEAR))
    x = np.arange(10.0)
    X = np.column_stack([x, 2 * x])
    with pytest.raises(RegressionError):
        fit(X, x + 1, spec(ModelKind.MULTIPLE, ("a", "b")))
    with pytest.raises(RegressionError):
        fit(np.array([1.0, 1.0, 2.0, 2.0, 2.0]), np.arange(5.0), spec(ModelKind.POLYNOMIAL, degree=3))


def test_compare_prefers_quadratic_for_quadratic_data():
    rng = np.random.default_rng(7)
    x = np.linspace(1, 10, 50)
    y = 3 + 0.5 * (x - 6) ** 2 + rng.normal(0, 0.3, x.size)
    rows = compare_models(x, y, "x", "y")
    assert rows[0].label.startswith("Polynomial")
    assert rows[0].cv_rmse < next(r for r in rows if r.label == "Linear").cv_rmse


def test_report_contains_key_sections(linear_data):
    x, y = linear_data
    text = build_report(fit(x, y, spec(ModelKind.LINEAR)))
    for needle in ("REGRESSION REPORT", "Equation", "Coefficients", "R-squared", "Jarque-Bera"):
        assert needle in text
