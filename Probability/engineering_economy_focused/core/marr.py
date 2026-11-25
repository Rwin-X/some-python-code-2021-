"""Building a MARR from the cost of capital plus a risk premium."""


def build_marr(equity: float, cost_equity: float, cost_debt: float, tax: float, premium: float) -> dict:
    """All rates and shares as fractions. MARR = WACC + risk premium."""
    if not 0 <= equity <= 1:
        raise ValueError("Equity share must be between 0% and 100%")
    if not 0 <= tax < 1:
        raise ValueError("Tax rate must be between 0% and 100%")
    debt = 1 - equity
    debt_after_tax = cost_debt * (1 - tax)
    wacc = equity * cost_equity + debt * debt_after_tax
    return {"debt_share": debt, "debt_after_tax": debt_after_tax, "wacc": wacc,
            "marr": wacc + premium}
