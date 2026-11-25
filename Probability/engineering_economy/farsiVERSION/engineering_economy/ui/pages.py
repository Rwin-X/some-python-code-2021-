"""All calculator pages. Each page only formats; the math lives in core/."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem, QWidget)

from core import (alternatives, cashflow, depreciation, economy, factors, loan,
                  rates, tax)
from ui.format import fmt, pct, pct_list
from ui.i18n import header, plain
from ui.page import Output, Page
from ui.widgets.chart import ProfileChart
from ui.widgets.form import Field

DEP_METHODS = depreciation.METHODS
MACRS_CLASSES = depreciation.MACRS_CLASSES


class FactorsPage(Page):
    title, section = "Factors", "factors"
    fields = (Field("i", "Interest rate i (%)", 12), Field("n", "Periods n", 8, kind="int"),
              Field("X", "Amount X", 50000), Field("G", "Arithmetic gradient G", 2000),
              Field("g", "Geometric rate g (%)", 5))

    def compute(self, v):
        rows = factors.factor_table(v["i"] / 100, v["n"], v["X"], v["G"], v["g"] / 100)
        cols = ["Symbol", "Description", "Factor", "Applied", "Result"]
        return Output(tables=[("", cols, [(r.symbol, r.description, fmt(r.factor, 6),
                                           r.applied, fmt(r.result)) for r in rows])])


class RatesPage(Page):
    title, section, sub = "Rates", "interest", "nominal_to_effective"
    fields = (Field("mode", "Direction", "Nominal to effective",
                    ("Nominal to effective", "Effective to nominal")),
              Field("r", "Rate (%)", 14),
              Field("m", "Compounding per year (0 = continuous)", 12, kind="int"),
              Field("P", "Principal", 200000), Field("years", "Years", 3))

    def compute(self, v):
        r, m = v["r"] / 100, v["m"]
        if v["mode"].startswith("Nominal"):
            d = rates.nominal_to_effective(r, m, v["P"], v["years"])
            items = [("Compounding", "continuous" if m == 0 else f"{m} per year"),
                     ("Rate per period", pct(d["period_rate"])),
                     ("Effective annual rate", pct(d["effective"])),
                     ("Future value (compound)", fmt(d["fv_compound"])),
                     ("Future value (simple)", fmt(d["fv_simple"])),
                     ("Doubling time (years)", fmt(d["doubling_years"], 3))]
        else:
            d = rates.effective_to_nominal(r, m)
            items = [("Effective annual rate", pct(r)), ("Nominal rate", pct(d["nominal"])),
                     ("Rate per period", pct(d["period_rate"])),
                     ("Continuous equivalent", pct(d["continuous"]))]
        return Output(items=items)


class CashFlowPage(Page):
    title, section = "Cash flow", "cash_flow"
    fields = (Field("cash_flows", "Cash flows, periods 0 to n", [-450000, 95000, 110000, 125000,
                                                                 135000, 140000, 140000, 135000,
                                                                 200000], kind="list"),
              Field("marr", "MARR (%)", 15), Field("reinvestment_rate", "Reinvestment rate (%)", 12),
              Field("finance_rate", "Finance rate (%)", 10))

    def build_bottom(self, layout):
        note = QLabel(plain("NPV profile"))
        note.setObjectName("tertiaryLabel")
        layout.addWidget(note)
        self.chart = ProfileChart()
        layout.addWidget(self.chart, 1)

    def compute(self, v):
        cfs, marr = v["cash_flows"], v["marr"] / 100
        r = cashflow.analyze(cfs, marr, v["reinvestment_rate"] / 100, v["finance_rate"] / 100)
        decision = "Accept" if r.accept else "Reject"
        items = [("Present worth", fmt(r.pw)), ("Future worth", fmt(r.fw)),
                 ("Annual worth", fmt(r.aw)), ("IRR", pct_list(r.irr)), ("MIRR", pct(r.mirr)),
                 ("Payback (years)", fmt(r.payback) if r.payback is not None else "not recovered"),
                 ("Discounted payback (years)",
                  fmt(r.discounted_payback) if r.discounted_payback is not None else "not recovered"),
                 ("Benefit / cost", fmt(r.benefit_cost, 3)), ("Decision at MARR", decision)]
        if len(r.irr) > 1:
            items.append(("Note", "Multiple IRRs: judge by PW"))
        rates_, values = cashflow.npv_profile(cfs, marr, r.irr)
        return Output(items=items, data=(rates_, values, marr, r.irr))

    def after_render(self, out):
        self.chart.set_data(*out.data)


class AlternativesPage(Page):
    title, section = "Alternatives", "alternatives"
    fields = (Field("marr", "MARR (%)", 15),)
    COLS = ["Name", "Initial", "Benefit/yr", "Cost/yr", "Salvage", "Life"]
    DEFAULT = [("A (semi-automatic CNC)", 450000, 230000, 120000, 50000, 8),
               ("B (robotic cell)", 780000, 330000, 150000, 120000, 12),
               ("C (upgrade existing machines)", 180000, 140000, 90000, 15000, 6)]

    def build_top(self, layout):
        self.alt_table = QTableWidget(0, len(self.COLS))
        self.alt_table.setHorizontalHeaderLabels([header(c) for c in self.COLS])
        self.alt_table.verticalHeader().setVisible(False)
        self.alt_table.verticalHeader().setDefaultSectionSize(26)
        self.alt_table.setShowGrid(False)
        self.alt_table.setFixedHeight(142)
        self.alt_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        hdr = self.alt_table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for row in self.DEFAULT:
            self._add_row(row)
        bar = QHBoxLayout()
        for text, slot in ((plain("Add row"), lambda: self._add_row(("New", 0, 0, 0, 0, 5))),
                           (plain("Remove row"), self._remove_row)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            bar.addWidget(b)
        bar.addStretch()
        layout.addWidget(self.alt_table)
        layout.addLayout(bar)

    def _add_row(self, row):
        r = self.alt_table.rowCount()
        self.alt_table.insertRow(r)
        for c, val in enumerate(row):
            item = QTableWidgetItem(str(val))
            if c:
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.alt_table.setItem(r, c, item)

    def _remove_row(self):
        r = self.alt_table.currentRow()
        if r >= 0:
            self.alt_table.removeRow(r)

    def _read_alts(self):
        alts = []
        for r in range(self.alt_table.rowCount()):
            cell = lambda c: self.alt_table.item(r, c).text().replace(",", "").strip()
            try:
                alts.append(alternatives.Alt(cell(0) or f"Alt {r + 1}", float(cell(1)), float(cell(2)),
                                             float(cell(3)), float(cell(4)), int(float(cell(5)))))
            except (ValueError, AttributeError):
                raise ValueError(f"Row {r + 1}: all columns except Name must be numbers")
        return alts

    def values(self):
        v = super().values()
        v["alts"] = self._read_alts()
        return v

    def load(self, data):
        super().load(data)
        if data.get("alternatives"):
            self.alt_table.setRowCount(0)
            for a in data["alternatives"]:
                self._add_row((a["name"], a["initial"], a["annual_benefit"], a["annual_cost"],
                               a["salvage"], a["life"]))

    def compute(self, v):
        c = alternatives.compare(v["alts"], v["marr"] / 100)
        rows = [(r.name, fmt(r.pw), fmt(r.aw), pct(r.irr)) for r in c.rows]
        steps = [(s.label, fmt(s.delta_pw), pct(s.ror),
                  "Accept" if s.accepted else "Reject")
                 for s in c.steps]
        return Output(
            items=[("Selected", c.selected or "none (all have negative PW)"),
                   ("Analysis period", f"{c.horizon} years (LCM of lives)")],
            tables=[("Worth over the analysis period", ["Name", "PW", "AW", "IRR"], rows),
                    ("Incremental analysis", ["Comparison", "Delta PW", "Incremental ROR", "Decision"], steps)])


class DepreciationPage(Page):
    title, section = "Depreciation", "depreciation"
    fields = (Field("method", "Method", DEP_METHODS[0], DEP_METHODS),
              Field("B", "First cost", 450000), Field("S", "Salvage value", 50000),
              Field("N", "Life (years)", 8, kind="int"), Field("db_factor", "DB factor (2 = DDB)", 2),
              Field("macrs_class", "MACRS class (years)", 7, MACRS_CLASSES, "int"))

    def compute(self, v):
        rows = depreciation.schedule(v["method"], v["B"], v["S"], v["N"], v["db_factor"], v["macrs_class"])
        table = [(y, fmt(d) if y else "", fmt(a) if y else "", fmt(b)) for y, d, a, b in rows]
        return Output(tables=[("", ["Year", "Depreciation", "Accumulated", "Book value"], table)])


class LoanPage(Page):
    title, section = "Loan", "loan"
    fields = (Field("amount", "Loan amount", 300000), Field("annual_rate_pct", "Annual rate (%)", 12),
              Field("term_years", "Term (years)", 5), Field("payments_per_year", "Payments per year", 12, kind="int"),
              Field("type", "Type", "Equal payments", ("Equal payments", "Equal principal")))

    def compute(self, v):
        r = loan.amortize(v["amount"], v["annual_rate_pct"] / 100, v["term_years"],
                          v["payments_per_year"], v["type"])
        items = [("Rate per period", pct(r.period_rate)), ("Payments", str(r.periods)),
                 ("First payment", fmt(r.first_payment)), ("Last payment", fmt(r.last_payment)),
                 ("Total interest", fmt(r.total_interest)),
                 ("Total paid", fmt(v["amount"] + r.total_interest))]
        rows = [(k, fmt(p), fmt(i), fmt(pr), fmt(b)) for k, p, i, pr, b in r.rows]
        return Output(items=items, tables=[("", ["Period", "Payment", "Interest", "Principal", "Balance"], rows)])


class TaxPage(Page):
    title, section = "After-tax", "after_tax"
    fields = (Field("P", "First cost", 450000), Field("S", "Salvage value", 50000),
              Field("N", "Life (years)", 8, kind="int"), Field("revenue", "Annual revenue or savings", 230000),
              Field("operating_cost", "Annual operating cost", 120000), Field("tax_rate_pct", "Tax rate (%)", 25),
              Field("marr_pct", "After-tax MARR (%)", 12),
              Field("method", "Depreciation", DEP_METHODS[3], DEP_METHODS),
              Field("db_factor", "DB factor", 2),
              Field("macrs_class", "MACRS class (years)", 7, MACRS_CLASSES, "int"))

    def compute(self, v):
        r = tax.after_tax(v["P"], v["S"], v["N"], v["revenue"], v["operating_cost"], v["tax_rate_pct"] / 100,
                          v["marr_pct"] / 100, v["method"], v["db_factor"], v["macrs_class"])
        items = [("After-tax PW", fmt(r.pw)), ("After-tax AW", fmt(r.aw)), ("After-tax IRR", pct_list(r.irr)),
                 ("Total tax paid", fmt(r.total_tax)), ("Book value at end of life", fmt(r.book_value)),
                 ("Decision", "Accept" if r.pw > 0 else "Reject")]
        rows = [(y, fmt(b), fmt(d) if y else "", fmt(ti) if y else "", fmt(tx) if y else "", fmt(a))
                for y, b, d, ti, tx, a in r.rows]
        return Output(items=items, tables=[("", ["Year", "BTCF", "Depreciation", "Taxable income", "Tax", "ATCF"], rows)])


class InflationPage(Page):
    title, section = "Inflation", "inflation"
    fields = (Field("i", "Market interest rate i (%)", 15), Field("f", "Inflation rate f (%)", 6),
              Field("amount", "Amount today", 100000), Field("years", "Years", 5))

    def compute(self, v):
        d = economy.inflation(v["i"] / 100, v["f"] / 100, v["amount"], v["years"])
        return Output(items=[
            ("Real interest rate", pct(d["real_rate"])),
            ("Cost of today's amount, then-dollars", fmt(d["then_dollars"])),
            ("Purchasing power of amount, today's dollars", fmt(d["purchasing_power"])),
            ("Future value at market rate, then-dollars", fmt(d["fv_market"])),
            ("Same future value, today's dollars", fmt(d["fv_real"]))])


class CapitalizedPage(Page):
    title, section = "Capitalized cost", "capitalized_cost"
    fields = (Field("P", "Initial cost", 250000), Field("A", "Annual cost", 12000),
              Field("R", "Recurring cost", 40000), Field("k", "Recurs every (years)", 5, kind="int"),
              Field("i", "Interest rate (%)", 10))

    def compute(self, v):
        d = economy.capitalized_cost(v["P"], v["A"], v["R"], v["k"], v["i"] / 100)
        return Output(items=[("PW of annual cost", fmt(d["annual_pw"])),
                             ("PW of recurring cost", fmt(d["recurring_pw"])),
                             ("Capitalized cost", fmt(d["capitalized"])),
                             ("Equivalent annual cost", fmt(d["equivalent_annual"]))])


class BreakEvenPage(Page):
    title, section = "Break-even", "break_even"
    fields = (Field("plan1_fixed", "Plan 1 fixed cost / yr", 120000),
              Field("plan1_variable", "Plan 1 variable cost / unit", 24),
              Field("price", "Price / unit", 38),
              Field("plan2_fixed", "Plan 2 fixed cost / yr", 260000),
              Field("plan2_variable", "Plan 2 variable cost / unit", 17))

    def compute(self, v):
        d = economy.break_even(v["plan1_fixed"], v["plan1_variable"], v["price"],
                               v["plan2_fixed"], v["plan2_variable"])
        items = [("Plan 1 break-even units", fmt(d["plan1_units"], 1)),
                 ("Plan 1 break-even revenue", fmt(d["plan1_revenue"])),
                 ("Plan 1 contribution margin", pct(d["plan1_margin"], 2)),
                 ("Plan 2 break-even units", fmt(d["plan2_units"], 1)),
                 ("Equal-cost volume of the two plans", fmt(d["crossover"], 1)),
                 ("Cheaper above that volume", d["cheaper_above"] or "n/a")]
        return Output(items=items)


ALL_PAGES = (FactorsPage, RatesPage, CashFlowPage, AlternativesPage, DepreciationPage,
             LoanPage, TaxPage, InflationPage, CapitalizedPage, BreakEvenPage)
