"""Inflation, capitalized cost and break-even analysis."""
from core.factors import af


def inflation(i: float, f: float, amount: float, years: float) -> dict:
    if i <= -1 or f <= -1:
        raise ValueError("Rates must be greater than -100%")
    real = (1 + i) / (1 + f) - 1
    return {
        "real_rate": real,
        "then_dollars": amount * (1 + f) ** years,
        "purchasing_power": amount / (1 + f) ** years,
        "fv_market": amount * (1 + i) ** years,
        "fv_real": amount * (1 + real) ** years,
    }


def capitalized_cost(first: float, annual: float, recurring: float, every: int, i: float) -> dict:
    if i <= 0 or every < 1:
        raise ValueError("Need i > 0 and a recurring period of at least 1 year")
    annual_pw = annual / i
    recurring_pw = recurring * af(i, every) / i
    total = first + annual_pw + recurring_pw
    return {"annual_pw": annual_pw, "recurring_pw": recurring_pw,
            "capitalized": total, "equivalent_annual": total * i}


def break_even(f1: float, v1: float, price: float, f2: float, v2: float) -> dict:
    out = {"plan1_units": None, "plan1_revenue": None, "plan1_margin": None,
           "plan2_units": None, "crossover": None, "cheaper_above": None}
    if price > v1:
        out["plan1_units"] = f1 / (price - v1)
        out["plan1_revenue"] = out["plan1_units"] * price
        out["plan1_margin"] = (price - v1) / price
    if price > v2:
        out["plan2_units"] = f2 / (price - v2)
    if v1 != v2:
        q = (f2 - f1) / (v1 - v2)
        if q > 0:
            out["crossover"] = q
            out["cheaper_above"] = "Plan 2" if v2 < v1 else "Plan 1"
    return out
