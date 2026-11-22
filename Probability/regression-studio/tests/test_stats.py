import numpy as np
import pytest

from regression_studio.core import stats

sps = pytest.importorskip("scipy.stats")
special = pytest.importorskip("scipy.special")


@pytest.mark.parametrize("a,b,x", [(0.5, 0.5, 0.3), (2, 3, 0.7), (10, 0.5, 0.99), (0.5, 20, 0.01), (30, 30, 0.5)])
def test_betainc_matches_scipy(a, b, x):
    assert stats.betainc(a, b, x) == pytest.approx(float(special.betainc(a, b, x)), rel=1e-9, abs=1e-12)


@pytest.mark.parametrize("t,dof", [(0.0, 5), (1.3, 3), (-2.5, 10), (8.0, 40), (0.1, 1)])
def test_t_two_sided_matches_scipy(t, dof):
    expected = 2 * sps.t.sf(abs(t), dof)
    assert stats.t_sf_two_sided(t, dof) == pytest.approx(expected, rel=1e-9, abs=1e-12)


@pytest.mark.parametrize("f,d1,d2", [(0.5, 1, 10), (3.2, 2, 20), (15.0, 4, 8), (1.0, 7, 7)])
def test_f_sf_matches_scipy(f, d1, d2):
    assert stats.f_sf(f, d1, d2) == pytest.approx(float(sps.f.sf(f, d1, d2)), rel=1e-9)


@pytest.mark.parametrize("q,dof", [(0.975, 1), (0.975, 5), (0.975, 37), (0.95, 12), (0.995, 3)])
def test_t_ppf_matches_scipy(q, dof):
    assert stats.t_ppf(q, dof) == pytest.approx(float(sps.t.ppf(q, dof)), rel=1e-8)


def test_jarque_bera_matches_scipy():
    values = np.random.default_rng(1).normal(size=200) ** 3
    stat, p = stats.jarque_bera(values)
    ref = sps.jarque_bera(values)
    assert stat == pytest.approx(ref.statistic, rel=1e-9)
    assert p == pytest.approx(ref.pvalue, rel=1e-9)


def test_qq_points_are_sorted_and_symmetric():
    theory, sample = stats.qq_points(np.array([3.0, 1.0, 2.0, 5.0]))
    assert list(sample) == [1.0, 2.0, 3.0, 5.0]
    assert theory == pytest.approx(-theory[::-1])


@pytest.mark.parametrize("x,dof", [(0.5, 1), (3.84, 1), (7.0, 3), (25.0, 10), (0.1, 6), (60.0, 4)])
def test_chi2_sf_matches_scipy(x, dof):
    assert stats.chi2_sf(x, dof) == pytest.approx(float(sps.chi2.sf(x, dof)), rel=1e-9, abs=1e-14)
