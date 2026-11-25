"""Single-project cash flow measures: PW, FW, AW, IRR, MIRR, payback, B/C."""
from dataclasses import dataclass

from core.factors import ap


def npv(rate: float, cfs: list[float]) -> float:
    """Present worth via Horner's rule (fast, no per-term exponentiation)."""
    if rate <= -1:
        raise ValueError("Rate must be greater than -100%")
    v = 1.0 / (1.0 + rate)
    acc = 0.0
    for c in reversed(cfs):
        acc = acc * v + c
    return acc


def irr_all(cfs: list[float], lo: float = -0.9, hi: float = 10.0, steps: int = 2000) -> list[float]:
    """All real roots of NPV(r) = 0 in (lo, hi): sign-change scan + bisection."""
    if not (any(c > 0 for c in cfs) and any(c < 0 for c in cfs)):
        return []
    roots: list[float] = []
    prev_r, prev_v = lo, npv(lo, cfs)
    for k in range(1, steps + 1):
        r = lo + (hi - lo) * k / steps
        v = npv(r, cfs)
        if prev_v == 0:
            roots.append(prev_r)
        elif prev_v * v < 0:
            a, b = prev_r, r
            for _ in range(80):
                m = (a + b) / 2
                if npv(a, cfs) * npv(m, cfs) <= 0:
                    b = m
                else:
                    a = m
            roots.append((a + b) / 2)
        prev_r, prev_v = r, v
    return roots


def mirr(cfs: list[float], reinvest: float, finance: float):
    n = len(cfs) - 1
    fv = sum(c * (1 + reinvest) ** (n - t) for t, c in enumerate(cfs) if c > 0)
    pv = sum(-c / (1 + finance) ** t for t, c in enumerate(cfs) if c < 0)
    if fv <= 0 or pv <= 0:
        return None
    return (fv / pv) ** (1 / n) - 1


def payback(cfs: list[float], rate: float = 0.0):
    """Payback period in years (linear interpolation); None if never recovered."""
    cum = 0.0
    for t, c in enumerate(cfs):
        d = c / (1 + rate) ** t
        prev, cum = cum, cum + d
        if t == 0:
            if cum >= 0:
                return 0.0
        elif prev < 0 <= cum:
            return t - 1 + (-prev) / d
    return None


def benefit_cost(cfs: list[float], rate: float):
    pb = sum(c / (1 + rate) ** t for t, c in enumerate(cfs) if c > 0)
    pc = sum(-c / (1 + rate) ** t for t, c in enumerate(cfs) if c < 0)
    return pb / pc if pc > 0 else None


@dataclass(frozen=True)
class CashFlowResult:
    pw: float
    fw: float
    aw: float
    irr: list
    mirr: float | None
    payback: float | None
    discounted_payback: float | None
    benefit_cost: float | None
    accept: bool


def analyze(cfs: list[float], marr: float, reinvest: float, finance: float) -> CashFlowResult:
    if len(cfs) < 2:
        raise ValueError("Enter at least two cash flows (periods 0 and 1)")
    n = len(cfs) - 1
    pw = npv(marr, cfs)
    roots = irr_all(cfs)
    accept = roots[0] >= marr if roots else pw > 0
    return CashFlowResult(
        pw=pw, fw=pw * (1 + marr) ** n, aw=pw * ap(marr, n), irr=roots,
        mirr=mirr(cfs, reinvest, finance), payback=payback(cfs),
        discounted_payback=payback(cfs, marr), benefit_cost=benefit_cost(cfs, marr),
        accept=accept,
    )


def npv_profile(cfs: list[float], marr: float, roots: list[float], points: int = 80):
    """Return (rates, values) sampled from 0 up to a sensible maximum rate."""
    top = max(roots) if roots else 0.0
    rmax = max(0.5, 1.3 * top, 1.5 * marr)
    rates = [rmax * k / points for k in range(points + 1)]
    return rates, [npv(r, cfs) for r in rates]
