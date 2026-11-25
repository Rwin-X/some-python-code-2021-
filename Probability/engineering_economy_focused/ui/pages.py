"""The six pages. Each page only formats; the math lives in core/."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QPushButton

from core import cashflow, factors, marr as marr_core, rates
from ui.format import fmt, pct, pct_list
from ui.i18n import plain
from ui.page import Output, Page
from ui.widgets.chart import ProfileChart
from ui.widgets.diagram import CashFlowDiagram
from ui.widgets.form import Field

DEFAULT_FLOWS = [-450000, 95000, 110000, 125000, 135000, 140000, 140000, 135000, 200000]
CASH_FLOWS = Field("cash_flows", "Cash flows, periods 0 to n", DEFAULT_FLOWS, kind="list")
MARR_FIELD = Field("marr", "MARR (%)", 15)


def decision_text(flag):
    return "n/a" if flag is None else ("Accept" if flag else "Reject")


def add_chart(page, layout):
    caption = QLabel(plain("NPV profile"))
    caption.setObjectName("tertiaryLabel")
    layout.addWidget(caption)
    page.chart = ProfileChart()
    layout.addWidget(page.chart, 1)


class InterestPage(Page):
    title, section = "Interest rate", "interest"
    fields = (Field("mode", "Direction", "Nominal to effective", ("Nominal to effective", "Effective to nominal")),
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
                     ("Interest earned (simple)", fmt(d["interest_simple"])),
                     ("Interest earned (compound)", fmt(d["interest_compound"])),
                     ("Future value (simple)", fmt(d["fv_simple"])),
                     ("Future value (compound)", fmt(d["fv_compound"])),
                     ("Doubling time (years)", fmt(d["doubling_years"], 3))]
        else:
            d = rates.effective_to_nominal(r, m)
            items = [("Effective annual rate", pct(r)), ("Nominal rate", pct(d["nominal"])),
                     ("Rate per period", pct(d["period_rate"])),
                     ("Continuous equivalent", pct(d["continuous"]))]
        return Output(items=items)


class CashFlowPage(Page):
    title, section = "Cash flow", "cash_flow"
    fields = (CASH_FLOWS, MARR_FIELD)

    def build_top(self, layout):
        self.diagram = CashFlowDiagram(190)
        layout.addWidget(self.diagram)

    def compute(self, v):
        rate = v["marr"] / 100
        w = cashflow.worth(v["cash_flows"], rate)
        items = [("Net total", fmt(w.total)), ("Present worth", fmt(w.pw)),
                 ("Future worth", fmt(w.fw)), ("Annual worth", fmt(w.aw))]
        rows = [(t, fmt(c), fmt(cum), fmt(d), fmt(cd)) for t, c, cum, d, cd in w.rows]
        cols = ["Period", "Cash flow", "Cumulative", "Discounted", "Cum. discounted"]
        return Output(items=items, tables=[("Cash flow table", cols, rows)],
                      data=(v["cash_flows"], f"i = {v['marr']:g}%"))

    def after_render(self, out):
        self.diagram.set_flows(out.data[0], "", out.data[1])


class RorPage(Page):
    title, section = "ROR", "ror"
    fields = (CASH_FLOWS,)

    def build_bottom(self, layout):
        add_chart(self, layout)

    def compute(self, v):
        r = cashflow.ror_report(v["cash_flows"])
        items = [("ROR", pct_list(r.roots)), ("Sign changes in cash flow", str(r.sign_changes))]
        if r.bracket and r.estimate is not None:
            items += [("Bracketing trial rates", f"{pct(r.bracket[0], 1)} and {pct(r.bracket[1], 1)}"),
                      ("Interpolated estimate", pct(r.estimate)),
                      ("Interpolation error", f"{(r.estimate - r.roots[0]) * 100:+.3f} pts")]
        if len(r.roots) > 1:
            items.append(("Note", "Several roots: ROR is ambiguous, use PW"))
        elif not r.roots:
            items.append(("Note", "No ROR exists for this cash flow"))
        table = [(pct(rate, 1), fmt(val)) for rate, val in r.trial]
        return Output(items=items, tables=[("Trial and error", ["Trial rate", "NPV"], table)],
                      data=(*r.profile, None, r.roots))

    def after_render(self, out):
        self.chart.set_data(*out.data)


class MarrPage(Page):
    title, section = "MARR", "marr"
    fields = (Field("equity_pct", "Equity share (%)", 60), Field("cost_equity_pct", "Cost of equity (%)", 16),
              Field("cost_debt_pct", "Cost of debt (%)", 12), Field("tax_pct", "Tax rate (%)", 25),
              Field("premium_pct", "Risk premium (%)", 1.8))

    def build_bottom(self, layout):
        self._marr_pct = None
        self.apply_btn = QPushButton(plain("Use as project MARR"))
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._apply)
        layout.addWidget(self.apply_btn, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()

    def compute(self, v):
        d = marr_core.build_marr(v["equity_pct"] / 100, v["cost_equity_pct"] / 100, v["cost_debt_pct"] / 100,
                                 v["tax_pct"] / 100, v["premium_pct"] / 100)
        items = [("Debt share", pct(d["debt_share"], 1)), ("After-tax cost of debt", pct(d["debt_after_tax"])),
                 ("WACC", pct(d["wacc"])), ("MARR", pct(d["marr"]))]
        return Output(items=items, data=d["marr"] * 100)

    def after_render(self, out):
        self._marr_pct = round(out.data, 6)
        self.apply_btn.setEnabled(True)

    def _apply(self):
        self.shared_changed.emit({"marr": self._marr_pct})
        self.set_status(plain("Applied to the project"))


class ComparePage(Page):
    title, section = "ROR vs MARR", "ror_vs_marr"
    fields = (CASH_FLOWS, MARR_FIELD)

    def build_bottom(self, layout):
        add_chart(self, layout)

    def compute(self, v):
        d = cashflow.decide(v["cash_flows"], v["marr"] / 100)
        items = [("ROR", pct(d.ror) if d.ror is not None else pct_list(d.roots)), ("MARR", pct(d.marr)),
                 ("Difference (ROR - MARR)", "n/a" if d.difference is None else f"{d.difference * 100:+.3f} pts"),
                 ("Present worth at MARR", fmt(d.pw)),
                 ("Decision by ROR rule", decision_text(d.by_ror)),
                 ("Decision by PW rule", decision_text(d.by_pw)),
                 ("Rules agree", "n/a" if d.agree is None else ("Yes" if d.agree else "No"))]
        if d.by_ror is None:
            items.append(("Note", "Several roots: ROR is ambiguous, use PW" if len(d.roots) > 1
                          else "No ROR exists for this cash flow"))
        rows = [(pct(m, 1) + (" *" if abs(m - d.marr) < 1e-9 else ""), fmt(pw), "Accept" if ok else "Reject")
                for m, pw, ok in d.sensitivity]
        return Output(items=items, tables=[("Decision as MARR changes", ["MARR", "PW", "Decision"], rows)],
                      data=(*d.profile, d.marr, d.roots))

    def after_render(self, out):
        self.chart.set_data(*out.data)


class DiagramPage(Page):
    title, section = "P-A-F-i", "diagram"
    fields = (Field("given", "Given", "P", ("P", "A", "F")), Field("amount", "Amount", 100000),
              Field("i", "Interest rate i (%)", 15), Field("n", "Periods n", 8, kind="int"))

    def build_top(self, layout):
        self.rows = {k: CashFlowDiagram(116) for k in ("P", "A", "F")}
        for d in self.rows.values():
            layout.addWidget(d)

    def compute(self, v):
        e = factors.equivalent(v["given"], v["amount"], v["i"] / 100, v["n"])
        items = [("Present worth P", fmt(e["P"])), ("Annual amount A", fmt(e["A"])), ("Future worth F", fmt(e["F"]))]
        table = [(sym, desc, fmt(val, 6)) for sym, desc, val in e["factors"]]
        return Output(items=items, tables=[("", ["Symbol", "Description", "Factor"], table)],
                      data=(v["n"], e["P"], e["A"], e["F"], f"i = {v['i']:g}%"))

    def after_render(self, out):
        n, P, A, F, caption = out.data
        self.rows["P"].set_flows([P] + [0.0] * n, "P", caption)
        self.rows["A"].set_flows([0.0] + [A] * n, "A", caption)
        self.rows["F"].set_flows([0.0] * n + [F], "F", caption)


ALL_PAGES = (InterestPage, CashFlowPage, RorPage, MarrPage, ComparePage, DiagramPage)
