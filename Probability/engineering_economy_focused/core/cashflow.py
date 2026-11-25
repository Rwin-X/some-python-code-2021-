"""Cash flow worth, rate of return (ROR), and the ROR-versus-MARR decision."""
import math
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


def _check(cfs: list[float]) -> None:
    if len(cfs) < 2:
        raise ValueError("Enter at least two cash flows (periods 0 and 1)")


def sign_changes(cfs: list[float]) -> int:
    nz = [c for c in cfs if c != 0]
    return sum(1 for a, b in zip(nz, nz[1:]) if a * b < 0)


# ---- cash flow page -----------------------------------------------------------
@dataclass(frozen=True)
class Worth:
    pw: float
    fw: float
    aw: float
    total: float
    rows: list  # (period, cash flow, cumulative, discounted, cumulative discounted)


def worth(cfs: list[float], rate: float) -> Worth:
    _check(cfs)
    n = len(cfs) - 1
    pw = npv(rate, cfs)
    rows, cum, cumd = [], 0.0, 0.0
    for t, c in enumerate(cfs):
        d = c / (1 + rate) ** t
        cum, cumd = cum + c, cumd + d
        rows.append((t, c, cum, d, cumd))
    return Worth(pw, pw * (1 + rate) ** n, pw * ap(rate, n), sum(cfs), rows)


# ---- ROR page ------------------------------------------------------------------
@dataclass(frozen=True)
class RorReport:
    roots: list
    sign_changes: int
    trial: list          # (trial rate, NPV)
    bracket: tuple | None  # (r1, r2) trial rates around the first root
    estimate: float | None  # linear interpolation between the bracket
    profile: tuple       # (rates, values) for the chart


def npv_profile(cfs: list[float], marr: float | None, roots: list[float], points: int = 80):
    top = max(roots) if roots else 0.0
    rmax = max(0.5, 1.3 * top, 1.5 * (marr or 0.0))
    rates = [rmax * k / points for k in range(points + 1)]
    return rates, [npv(r, cfs) for r in rates]


def ror_report(cfs: list[float], step: float = 0.05) -> RorReport:
    _check(cfs)
    roots = irr_all(cfs)
    lo = 0.0
    hi = 0.5
    if roots:
        lo = min(0.0, math.floor(min(roots) / step) * step)
        hi = max(0.5, math.ceil(1.4 * max(roots) / step) * step)
    count = min(int(round((hi - lo) / step)), 60)
    trial = [(lo + k * step, npv(lo + k * step, cfs)) for k in range(count + 1)]
    bracket, estimate = None, None
    if roots:
        for (r1, v1), (r2, v2) in zip(trial, trial[1:]):
            if v1 * v2 < 0 and r1 <= roots[0] <= r2:
                bracket, estimate = (r1, r2), r1 + (r2 - r1) * v1 / (v1 - v2)
                trial = trial[:trial.index((r2, v2)) + 2]  # stop one step past the root
                break
    return RorReport(roots, sign_changes(cfs), trial, bracket, estimate,
                     npv_profile(cfs, None, roots))


# ---- ROR versus MARR -----------------------------------------------------------
@dataclass(frozen=True)
class Decision:
    roots: list
    ror: float | None        # defined only when the ROR is unique
    marr: float
    difference: float | None  # ROR - MARR
    pw: float
    by_ror: bool | None
    by_pw: bool
    agree: bool | None
    sensitivity: list        # (MARR, PW, accept)
    profile: tuple


def decide(cfs: list[float], marr: float) -> Decision:
    _check(cfs)
    roots = irr_all(cfs)
    pw = npv(marr, cfs)
    ror = roots[0] if len(roots) == 1 else None
    by_ror = None if ror is None else ror >= marr
    by_pw = pw >= 0
    grid = sorted({round(0.05 * k, 10) for k in range(1, 9)} | {marr})
    sens = [(m, npv(m, cfs), npv(m, cfs) >= 0) for m in grid]
    return Decision(roots, ror, marr, None if ror is None else ror - marr, pw, by_ror, by_pw,
                    None if by_ror is None else by_ror == by_pw, sens,
                    npv_profile(cfs, marr, roots))
