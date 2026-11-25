"""Mutually exclusive alternatives: PW/AW over the LCM of lives and incremental ROR."""
import math
from dataclasses import dataclass

from core.cashflow import irr_all, npv
from core.factors import ap


@dataclass(frozen=True)
class Alt:
    name: str
    initial: float
    benefit: float
    cost: float
    salvage: float
    life: int


@dataclass(frozen=True)
class AltRow:
    name: str
    pw: float
    aw: float
    irr: float | None


@dataclass(frozen=True)
class Step:
    label: str
    delta_pw: float
    ror: float | None
    accepted: bool
    kept: str


@dataclass(frozen=True)
class Comparison:
    horizon: int
    rows: list
    steps: list
    selected: str | None


def build_cf(a: Alt, horizon: int) -> list[float]:
    """Cash flow over the horizon with identical replacements at end of each life."""
    cf = [0.0] * (horizon + 1)
    for t in range(1, horizon + 1):
        cf[t] += a.benefit - a.cost
    for k in range(0, horizon, a.life):
        cf[k] -= a.initial
        cf[k + a.life] += a.salvage
    return cf


def compare(alts: list[Alt], marr: float, max_horizon: int = 300) -> Comparison:
    if len(alts) < 2:
        raise ValueError("Add at least two alternatives")
    if any(a.life < 1 for a in alts):
        raise ValueError("Every life must be at least 1 year")
    horizon = math.lcm(*[a.life for a in alts])
    if horizon > max_horizon:
        raise ValueError(f"LCM of lives is {horizon} years (limit {max_horizon})")
    cfs = [build_cf(a, horizon) for a in alts]

    rows = []
    for a, cf in zip(alts, cfs):
        pw = npv(marr, cf)
        roots = irr_all(cf)
        rows.append(AltRow(a.name, pw, pw * ap(marr, horizon), roots[0] if roots else None))

    order = sorted(range(len(alts)), key=lambda k: alts[k].initial)
    cost_only = all(a.benefit == 0 for a in alts)
    if cost_only:
        best, best_name, queue = cfs[order[0]], alts[order[0]].name, order[1:]
    else:
        best, best_name, queue = [0.0] * (horizon + 1), None, order

    steps = []
    for k in queue:
        diff = [x - y for x, y in zip(cfs[k], best)]
        dpw = npv(marr, diff)
        roots = irr_all(diff)
        accepted = dpw > 0
        steps.append(Step(f"{alts[k].name} vs {best_name or 'Do nothing'}", dpw,
                          roots[0] if roots else None, accepted, best_name or "Do nothing"))
        if accepted:
            best, best_name = cfs[k], alts[k].name
    return Comparison(horizon, rows, steps, best_name)
