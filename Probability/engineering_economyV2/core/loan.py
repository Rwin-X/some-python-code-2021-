"""Loan amortization: equal payments or equal principal."""
from dataclasses import dataclass

from core.factors import ap


@dataclass(frozen=True)
class LoanResult:
    period_rate: float
    periods: int
    rows: list  # (period, payment, interest, principal, balance)
    first_payment: float
    last_payment: float
    total_interest: float


def amortize(principal: float, annual_rate: float, years: float, per_year: int,
             kind: str = "Equal payments") -> LoanResult:
    if per_year < 1:
        raise ValueError("Payments per year must be at least 1")
    n = round(years * per_year)
    if n < 1 or principal <= 0:
        raise ValueError("Need a positive loan amount and at least one payment period")
    i = annual_rate / per_year
    bal, rows, total_int = principal, [], 0.0
    for k in range(1, n + 1):
        interest = bal * i
        pay = principal * ap(i, n) if kind == "Equal payments" else principal / n + interest
        princ = pay - interest
        bal = bal - princ if k < n else 0.0
        total_int += interest
        rows.append((k, pay, interest, princ, max(bal, 0.0)))
    return LoanResult(i, n, rows, rows[0][1], rows[-1][1], total_int)
