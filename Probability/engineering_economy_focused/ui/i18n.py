"""English -> Persian labels shown in parentheses next to the English text.

All translations live here so pages stay clean. Lookup is by exact English text;
unknown text is shown as-is. Persian is kept free of Latin tokens where possible
so mixed-direction text reads cleanly.
"""
import html

from ui.style import TEXT_TERTIARY

FA = {
    # app and navigation
    "Engineering Economy": "اقتصاد مهندسی",
    "Interest rate": "نرخ بهره", "Cash flow": "جریان نقدی", "ROR": "نرخ بازگشت سرمایه",
    "MARR": "حداقل نرخ جذاب", "ROR vs MARR": "مقایسه دو نرخ",
    "P-A-F-i": "نمودار جریان نقدی",
    "Calculate": "محاسبه", "Load dataset": "بارگذاری داده",
    "Use as project MARR": "استفاده به‌عنوان نرخ جذاب پروژه",
    "Applied to the project": "در پروژه اعمال شد", "NPV profile": "نمودار ارزش فعلی خالص",

    # inputs
    "Direction": "جهت تبدیل", "Nominal to effective": "اسمی به مؤثر",
    "Effective to nominal": "مؤثر به اسمی", "Rate (%)": "نرخ",
    "Compounding per year (0 = continuous)": "دفعات مرکب‌سازی در سال؛ ۰ = پیوسته",
    "Principal": "اصل پول", "Years": "سال",
    "Cash flows, periods 0 to n": "جریان‌های نقدی هر دوره", "MARR (%)": "حداقل نرخ جذاب",
    "Equity share (%)": "سهم سرمایه شخصی", "Cost of equity (%)": "هزینه سرمایه شخصی",
    "Cost of debt (%)": "هزینه بدهی", "Tax rate (%)": "نرخ مالیات", "Risk premium (%)": "صرف ریسک",
    "Given": "مقدار معلوم", "P": "ارزش فعلی", "A": "مبلغ یکنواخت", "F": "ارزش آتی",
    "Amount": "مبلغ", "Interest rate i (%)": "نرخ بهره", "Periods n": "تعداد دوره‌ها",

    # results: interest rate
    "Compounding": "مرکب‌سازی", "Rate per period": "نرخ هر دوره",
    "Effective annual rate": "نرخ مؤثر سالانه", "Nominal rate": "نرخ اسمی",
    "Continuous equivalent": "معادل پیوسته", "Interest earned (simple)": "بهره ساده",
    "Interest earned (compound)": "بهره مرکب", "Future value (simple)": "ارزش آتی ساده",
    "Future value (compound)": "ارزش آتی مرکب", "Doubling time (years)": "زمان دو برابر شدن، سال",
    # results: cash flow
    "Net total": "جمع خالص", "Present worth": "ارزش فعلی", "Future worth": "ارزش آتی",
    "Annual worth": "ارزش سالانه",
    # results: ROR
    "Sign changes in cash flow": "تغییر علامت در جریان نقدی",
    "Bracketing trial rates": "نرخ‌های آزمون اطراف ریشه", "Interpolated estimate": "برآورد با میان‌یابی",
    "Interpolation error": "خطای میان‌یابی", "Note": "نکته",
    "Several roots: ROR is ambiguous, use PW": "چند ریشه: نرخ بازگشت مبهم است؛ از ارزش فعلی استفاده کنید",
    "No ROR exists for this cash flow": "برای این جریان نقدی نرخ بازگشت وجود ندارد",
    # results: MARR
    "Debt share": "سهم بدهی", "After-tax cost of debt": "هزینه بدهی پس از مالیات",
    "WACC": "میانگین موزون هزینه سرمایه",
    # results: ROR vs MARR
    "Difference (ROR - MARR)": "تفاوت نرخ بازگشت و حداقل نرخ جذاب",
    "Present worth at MARR": "ارزش فعلی در حداقل نرخ جذاب",
    "Decision by ROR rule": "تصمیم بر اساس نرخ بازگشت", "Decision by PW rule": "تصمیم بر اساس ارزش فعلی",
    "Rules agree": "هم‌خوانی دو قاعده",
    # results: P-A-F-i
    "Present worth P": "ارزش فعلی", "Annual amount A": "مبلغ یکنواخت سالانه", "Future worth F": "ارزش آتی",

    # values
    "Accept": "پذیرش", "Reject": "رد", "Yes": "بله", "No": "خیر", "none": "ندارد",
    "continuous": "پیوسته",

    # tables
    "Cash flow table": "جدول جریان نقدی", "Trial and error": "آزمون و خطا",
    "Decision as MARR changes": "تصمیم با تغییر حداقل نرخ جذاب",
    "Period": "دوره", "Cumulative": "تجمعی", "Discounted": "تنزیل‌شده",
    "Cum. discounted": "تجمعی تنزیل‌شده", "Trial rate": "نرخ آزمون", "NPV": "ارزش فعلی خالص",
    "PW": "ارزش فعلی", "Decision": "تصمیم", "Symbol": "نماد", "Description": "شرح", "Factor": "ضریب",
    "Single payment compound amount": "مبلغ آتی پرداخت منفرد",
    "Single payment present worth": "ارزش فعلی پرداخت منفرد",
    "Sinking fund": "صندوق استهلاک", "Capital recovery": "بازیافت سرمایه",
    "Uniform series compound amount": "مبلغ آتی سری یکنواخت",
    "Uniform series present worth": "ارزش فعلی سری یکنواخت",
}


def plain(text: str) -> str:
    """'English (فارسی)' as plain text, or the text unchanged if untranslated."""
    fa = FA.get(text)
    return f"{text} ({fa})" if fa else text


def rich(text: str, size: int | None = None) -> str:
    """Rich text with the Persian part in the muted tertiary colour."""
    fa = FA.get(text)
    if not fa:
        return html.escape(text)
    style = (f"font-size:{size}px;" if size else "") + f"color:{TEXT_TERTIARY}"
    return f'{html.escape(text)} <span style="{style}">({fa})</span>'


def header(text: str) -> str:
    """Two-line table header: English, then (فارسی)."""
    fa = FA.get(text)
    return f"{text}\n({fa})" if fa else text
