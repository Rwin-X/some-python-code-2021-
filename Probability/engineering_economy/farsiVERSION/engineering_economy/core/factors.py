"""Interest factors for end-of-period compounding. Pure math, no Qt."""
from dataclasses import dataclass


def _zero(x: float) -> bool:
    return abs(x) < 1e-12


def fp(i, n):  # (F/P,i,n) single payment compound amount
    return (1 + i) ** n


def pf(i, n):  # (P/F,i,n) single payment present worth
    return (1 + i) ** -n


def af(i, n):  # (A/F,i,n) sinking fund
    return 1 / n if _zero(i) else i / ((1 + i) ** n - 1)


def ap(i, n):  # (A/P,i,n) capital recovery
    return 1 / n if _zero(i) else i * (1 + i) ** n / ((1 + i) ** n - 1)


def fa(i, n):  # (F/A,i,n) uniform series compound amount
    return n if _zero(i) else ((1 + i) ** n - 1) / i


def pa(i, n):  # (P/A,i,n) uniform series present worth
    return n if _zero(i) else ((1 + i) ** n - 1) / (i * (1 + i) ** n)


def pg(i, n):  # (P/G,i,n) arithmetic gradient present worth
    return n * (n - 1) / 2 if _zero(i) else (pa(i, n) - n * (1 + i) ** -n) / i


def ag(i, n):  # (A/G,i,n) arithmetic gradient uniform series
    return (n - 1) / 2 if _zero(i) else 1 / i - n / ((1 + i) ** n - 1)


def pa_geo(i, g, n):  # (P/A1,g,i,n) geometric gradient present worth
    if _zero(i - g):
        return n / (1 + i)
    return (1 - ((1 + g) / (1 + i)) ** n) / (i - g)


@dataclass(frozen=True)
class FactorRow:
    symbol: str
    description: str
    factor: float
    applied: str
    result: float


def factor_table(i: float, n: int, x: float, gradient: float, g: float) -> list[FactorRow]:
    if n < 1:
        raise ValueError("Periods n must be at least 1")
    if i <= -1 or g <= -1:
        raise ValueError("Rates must be greater than -100%")
    spec = [
        ("(F/P,i,n)", "Single payment compound amount", fp(i, n), "X as P -> F", x),
        ("(P/F,i,n)", "Single payment present worth", pf(i, n), "X as F -> P", x),
        ("(A/F,i,n)", "Sinking fund", af(i, n), "X as F -> A", x),
        ("(A/P,i,n)", "Capital recovery", ap(i, n), "X as P -> A", x),
        ("(F/A,i,n)", "Uniform series compound amount", fa(i, n), "X as A -> F", x),
        ("(P/A,i,n)", "Uniform series present worth", pa(i, n), "X as A -> P", x),
        ("(P/G,i,n)", "Arithmetic gradient present worth", pg(i, n), "G -> P", gradient),
        ("(A/G,i,n)", "Arithmetic gradient annual series", ag(i, n), "G -> A", gradient),
        ("(P/A1,g,i,n)", "Geometric gradient present worth", pa_geo(i, g, n), "X as A1 -> P", x),
    ]
    return [FactorRow(s, d, f, a, base * f) for s, d, f, a, base in spec]
