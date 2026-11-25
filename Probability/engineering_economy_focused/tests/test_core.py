import pytest

from core import cashflow, factors, marr, rates

CF = [-450000, 95000, 110000, 125000, 135000, 140000, 140000, 135000, 200000]


def test_equivalent_p_a_f():
    e = factors.equivalent("P", 100000, 0.15, 8)
    assert e["A"] == pytest.approx(22285.01, abs=0.01)
    assert e["F"] == pytest.approx(305902.29, abs=0.01)
    assert factors.equivalent("A", e["A"], 0.15, 8)["P"] == pytest.approx(100000, abs=0.01)
    assert factors.equivalent("F", e["F"], 0.15, 8)["P"] == pytest.approx(100000, abs=0.01)
    assert factors.pa(0.0, 5) == 5


def test_interest_rate_concepts():
    d = rates.nominal_to_effective(0.14, 12, 200000, 3)
    assert d["effective"] == pytest.approx(0.14934, abs=1e-5)
    assert d["interest_simple"] == pytest.approx(84000)
    assert d["interest_compound"] == pytest.approx(103653, abs=1)
    back = rates.effective_to_nominal(d["effective"], 12)
    assert back["nominal"] == pytest.approx(0.14, abs=1e-9)


def test_worth_and_table():
    w = cashflow.worth(CF, 0.15)
    assert w.pw == pytest.approx(121423.18, abs=0.01)
    assert w.total == 630000 and w.rows[-1][2] == 630000
    assert w.rows[0][3] == -450000  # period 0 is not discounted


def test_ror_and_interpolation():
    r = cashflow.ror_report(CF)
    assert r.roots[0] == pytest.approx(0.22008, abs=1e-5)
    assert r.sign_changes == 1
    assert r.bracket == (0.2, 0.25)
    assert r.estimate == pytest.approx(0.2216, abs=1e-4)  # linear interpolation overshoots slightly


def test_multiple_roots_and_no_root():
    assert len(cashflow.irr_all([-100, 230, -132])) == 2
    assert cashflow.ror_report([100, 50]).roots == []
    d = cashflow.decide([-100, 230, -132], 0.15)
    assert d.ror is None and d.by_ror is None and d.agree is None


def test_decision_ror_vs_marr():
    d = cashflow.decide(CF, 0.15)
    assert d.difference == pytest.approx(0.07008, abs=1e-5)
    assert d.by_ror and d.by_pw and d.agree
    rej = cashflow.decide(CF, 0.30)
    assert not rej.by_ror and not rej.by_pw and rej.agree
    # the ROR rule and PW rule always agree for a conventional cash flow
    for m in (0.05, 0.1, 0.2, 0.22, 0.23, 0.4):
        assert cashflow.decide(CF, m).agree


def test_marr_build():
    d = marr.build_marr(0.6, 0.16, 0.12, 0.25, 0.018)
    assert d["debt_after_tax"] == pytest.approx(0.09)
    assert d["wacc"] == pytest.approx(0.132)
    assert d["marr"] == pytest.approx(0.15)
    with pytest.raises(ValueError):
        marr.build_marr(1.2, 0.1, 0.1, 0.2, 0)
