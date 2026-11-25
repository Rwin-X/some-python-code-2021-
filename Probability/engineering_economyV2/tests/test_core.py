import math

import pytest

from core import alternatives, cashflow, depreciation, economy, factors, loan, rates, tax

CF = [-450000, 95000, 110000, 125000, 135000, 140000, 140000, 135000, 200000]


def test_factors_table_values():
    assert factors.pa(0.10, 5) == pytest.approx(3.7908, abs=1e-4)
    assert factors.ap(0.10, 5) == pytest.approx(0.2638, abs=1e-4)
    assert factors.pg(0.10, 5) == pytest.approx(6.8618, abs=1e-4)
    assert factors.ag(0.10, 5) == pytest.approx(1.8101, abs=1e-4)
    assert factors.pa(0.0, 5) == 5


def test_rates():
    d = rates.nominal_to_effective(0.14, 12, 200000, 3)
    assert d["effective"] == pytest.approx(0.14934, abs=1e-5)
    assert d["fv_compound"] == pytest.approx(303653, abs=1)
    assert rates.nominal_to_effective(0.12, 0, 1, 1)["effective"] == pytest.approx(math.exp(0.12) - 1)


def test_cashflow_measures():
    r = cashflow.analyze(CF, 0.15, 0.12, 0.10)
    assert r.pw == pytest.approx(121423, abs=1)
    assert r.irr[0] == pytest.approx(0.2201, abs=1e-4)
    assert r.mirr == pytest.approx(0.1703, abs=1e-4)
    assert r.payback == pytest.approx(3.89, abs=0.01)
    assert r.discounted_payback == pytest.approx(5.91, abs=0.01)
    assert r.benefit_cost == pytest.approx(1.27, abs=0.01)
    assert r.accept


def test_multiple_irr_roots():
    assert len(cashflow.irr_all([-100, 230, -132])) == 2  # roots at 10% and 20%


def test_alternatives_selects_b():
    alts = [alternatives.Alt("A", 450000, 230000, 120000, 50000, 8),
            alternatives.Alt("B", 780000, 330000, 150000, 120000, 12),
            alternatives.Alt("C", 180000, 140000, 90000, 15000, 6)]
    c = alternatives.compare(alts, 0.15)
    assert c.horizon == 24 and c.selected == "B"
    assert [round(r.pw) for r in c.rows] == [85955, 258912, 26706]


def test_depreciation():
    assert depreciation.charges("Straight line", 450000, 50000, 8)[0] == 50000
    assert depreciation.charges("MACRS (half-year)", 450000, 50000, 8, macrs_class=7)[0] == pytest.approx(64305)
    assert sum(depreciation.charges("Sum-of-years digits", 50000, 5000, 5)) == pytest.approx(45000)
    for cls, pcts in depreciation.MACRS.items():
        assert sum(pcts) == pytest.approx(100, abs=0.01), cls


def test_loan():
    r = loan.amortize(300000, 0.12, 5, 12)
    assert r.first_payment == pytest.approx(6673.33, abs=0.01)
    assert r.total_interest == pytest.approx(100400, abs=5)
    assert r.rows[-1][4] == 0


def test_after_tax():
    r = tax.after_tax(450000, 50000, 8, 230000, 120000, 0.25, 0.12, "MACRS (half-year)", macrs_class=7)
    assert r.pw == pytest.approx(51584, abs=1)
    assert r.irr[0] == pytest.approx(0.152, abs=1e-3)
    assert r.book_value == pytest.approx(0, abs=1e-6)


def test_economy():
    assert economy.inflation(0.15, 0.06, 100000, 5)["real_rate"] == pytest.approx(0.0849, abs=1e-4)
    assert economy.capitalized_cost(250000, 12000, 40000, 5, 0.10)["capitalized"] == pytest.approx(435519, abs=1)
    b = economy.break_even(120000, 24, 38, 260000, 17)
    assert b["plan1_units"] == pytest.approx(8571.4, abs=0.1)
    assert b["crossover"] == pytest.approx(20000)
