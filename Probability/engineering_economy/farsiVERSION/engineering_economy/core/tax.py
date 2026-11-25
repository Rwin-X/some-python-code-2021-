"""After-tax cash flow analysis with depreciation and tax on salvage gain or loss."""
from dataclasses import dataclass

from core.cashflow import irr_all, npv
from core.depreciation import charges
from core.factors import ap


@dataclass(frozen=True)
class TaxResult:
    rows: list  # (year, BTCF, depreciation, taxable income, tax, ATCF)
    pw: float
    aw: float
    irr: list
    total_tax: float
    book_value: float


def after_tax(first_cost, salvage, life, revenue, opex, tax_rate, marr,
              method, db_factor=2.0, macrs_class=5) -> TaxResult:
    if life < 1:
        raise ValueError("Life must be at least 1 year")
    deps = charges(method, first_cost, salvage, life, db_factor, macrs_class)

    def dep(t):
        return deps[t - 1] if t <= len(deps) else 0.0

    book = first_cost - sum(dep(t) for t in range(1, life + 1))
    rows = [(0, -first_cost, 0.0, 0.0, 0.0, -first_cost)]
    atcf, total_tax = [-first_cost], 0.0
    for t in range(1, life + 1):
        btcf = revenue - opex + (salvage if t == life else 0.0)
        taxable = revenue - opex - dep(t) + ((salvage - book) if t == life else 0.0)
        tax = taxable * tax_rate
        total_tax += tax
        atcf.append(btcf - tax)
        rows.append((t, btcf, dep(t), taxable, tax, btcf - tax))
    pw = npv(marr, atcf)
    return TaxResult(rows, pw, pw * ap(marr, life), irr_all(atcf), total_tax, book)
