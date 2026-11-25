"""Interest rate concepts: simple vs compound, nominal, effective, continuous."""
import math


def nominal_to_effective(r: float, m: int, principal: float, years: float) -> dict:
    """m = compounding periods per year; m = 0 means continuous compounding."""
    if m < 0:
        raise ValueError("Compounding per year cannot be negative")
    if m == 0:
        eff, period = math.exp(r) - 1, None
        fv = principal * math.exp(r * years)
    else:
        eff, period = (1 + r / m) ** m - 1, r / m
        fv = principal * (1 + r / m) ** (m * years)
    if eff <= -1:
        raise ValueError("Rate must give an effective rate above -100%")
    simple = principal * r * years
    return {
        "period_rate": period,
        "effective": eff,
        "fv_compound": fv,
        "fv_simple": principal + simple,
        "interest_compound": fv - principal,
        "interest_simple": simple,
        "doubling_years": math.log(2) / math.log(1 + eff) if eff > 0 else None,
    }


def effective_to_nominal(eff: float, m: int) -> dict:
    if m < 0:
        raise ValueError("Compounding per year cannot be negative")
    if eff <= -1:
        raise ValueError("Effective rate must be above -100%")
    cont = math.log(1 + eff)
    if m == 0:
        return {"nominal": cont, "period_rate": None, "continuous": cont}
    nominal = m * ((1 + eff) ** (1 / m) - 1)
    return {"nominal": nominal, "period_rate": nominal / m, "continuous": cont}
