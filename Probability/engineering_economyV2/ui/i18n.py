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
    "Factors": "ضرایب بهره", "Rates": "نرخ‌های بهره", "Cash flow": "جریان نقدی",
    "Alternatives": "گزینه‌ها", "Depreciation": "استهلاک", "Loan": "وام",
    "After-tax": "پس از مالیات", "Inflation": "تورم",
    "Capitalized cost": "هزینه سرمایه‌شده", "Break-even": "نقطه سر‌به‌سر",
    "Calculate": "محاسبه", "Load dataset": "بارگذاری داده",
    "Add row": "افزودن ردیف", "Remove row": "حذف ردیف",
    "NPV profile": "نمودار ارزش فعلی خالص",

    # input fields
    "Interest rate i (%)": "نرخ بهره", "Periods n": "تعداد دوره‌ها", "Amount X": "مبلغ",
    "Arithmetic gradient G": "گرادیان حسابی", "Geometric rate g (%)": "نرخ گرادیان هندسی",
    "Direction": "جهت تبدیل", "Nominal to effective": "اسمی به مؤثر",
    "Effective to nominal": "مؤثر به اسمی", "Rate (%)": "نرخ",
    "Compounding per year (0 = continuous)": "دفعات مرکب‌سازی در سال؛ ۰ = پیوسته",
    "Principal": "اصل پول", "Years": "سال",
    "Cash flows, periods 0 to n": "جریان‌های نقدی هر دوره",
    "MARR (%)": "حداقل نرخ بازده جذاب", "Reinvestment rate (%)": "نرخ سرمایه‌گذاری مجدد",
    "Finance rate (%)": "نرخ تأمین مالی",
    "Name": "نام", "Initial": "هزینه اولیه", "Benefit/yr": "منفعت سالانه",
    "Cost/yr": "هزینه سالانه", "Salvage": "ارزش اسقاط", "Life": "عمر",
    "Method": "روش", "First cost": "هزینه اولیه", "Salvage value": "ارزش اسقاط",
    "Life (years)": "عمر، سال", "DB factor (2 = DDB)": "ضریب موجودی نزولی",
    "DB factor": "ضریب موجودی نزولی", "MACRS class (years)": "کلاس استهلاک شتابان",
    "Straight line": "خط مستقیم", "Declining balance": "موجودی نزولی",
    "Sum-of-years digits": "مجموع ارقام سنوات", "MACRS (half-year)": "شتابان، نیم‌سال",
    "Loan amount": "مبلغ وام", "Annual rate (%)": "نرخ سالانه", "Term (years)": "مدت، سال",
    "Payments per year": "اقساط در سال", "Type": "نوع",
    "Equal payments": "اقساط مساوی", "Equal principal": "اصل مساوی",
    "Annual revenue or savings": "درآمد یا صرفه‌جویی سالانه",
    "Annual operating cost": "هزینه عملیاتی سالانه", "Tax rate (%)": "نرخ مالیات",
    "After-tax MARR (%)": "حداقل نرخ بازده پس از مالیات",
    "Market interest rate i (%)": "نرخ بهره بازار", "Inflation rate f (%)": "نرخ تورم",
    "Amount today": "مبلغ امروز", "Initial cost": "هزینه اولیه", "Annual cost": "هزینه سالانه",
    "Recurring cost": "هزینه تکرارشونده", "Recurs every (years)": "تکرار هر چند سال",
    "Interest rate (%)": "نرخ بهره",
    "Plan 1 fixed cost / yr": "هزینه ثابت طرح ۱ در سال",
    "Plan 1 variable cost / unit": "هزینه متغیر طرح ۱ هر واحد", "Price / unit": "قیمت هر واحد",
    "Plan 2 fixed cost / yr": "هزینه ثابت طرح ۲ در سال",
    "Plan 2 variable cost / unit": "هزینه متغیر طرح ۲ هر واحد",

    # result labels
    "Compounding": "مرکب‌سازی", "Rate per period": "نرخ هر دوره",
    "Effective annual rate": "نرخ مؤثر سالانه", "Future value (compound)": "ارزش آتی مرکب",
    "Future value (simple)": "ارزش آتی ساده", "Doubling time (years)": "زمان دو برابر شدن، سال",
    "Nominal rate": "نرخ اسمی", "Continuous equivalent": "معادل پیوسته",
    "Present worth": "ارزش فعلی", "Future worth": "ارزش آتی", "Annual worth": "ارزش سالانه",
    "IRR": "نرخ بازده داخلی", "MIRR": "نرخ بازده داخلی اصلاح‌شده",
    "Payback (years)": "دوره بازگشت سرمایه", "Discounted payback (years)": "بازگشت سرمایه تنزیل‌شده",
    "Benefit / cost": "نسبت منفعت به هزینه", "Decision at MARR": "تصمیم در نرخ جذاب",
    "Note": "نکته", "Multiple IRRs: judge by PW": "چند نرخ بازده؛ با ارزش فعلی تصمیم بگیرید",
    "Selected": "گزینه منتخب", "Analysis period": "دوره تحلیل",
    "Payments": "تعداد اقساط", "First payment": "قسط اول", "Last payment": "قسط آخر",
    "Total interest": "کل بهره", "Total paid": "کل پرداختی",
    "After-tax PW": "ارزش فعلی پس از مالیات", "After-tax AW": "ارزش سالانه پس از مالیات",
    "After-tax IRR": "نرخ بازده پس از مالیات", "Total tax paid": "کل مالیات پرداختی",
    "Book value at end of life": "ارزش دفتری پایان عمر", "Decision": "تصمیم",
    "Real interest rate": "نرخ بهره واقعی",
    "Cost of today's amount, then-dollars": "هزینه مبلغ امروز در آینده",
    "Purchasing power of amount, today's dollars": "قدرت خرید مبلغ به پول امروز",
    "Future value at market rate, then-dollars": "ارزش آتی با نرخ بازار",
    "Same future value, today's dollars": "همان ارزش آتی به پول امروز",
    "PW of annual cost": "ارزش فعلی هزینه سالانه", "PW of recurring cost": "ارزش فعلی هزینه تکرارشونده",
    "Equivalent annual cost": "هزینه سالانه معادل",
    "Plan 1 break-even units": "واحد سر‌به‌سر طرح ۱", "Plan 1 break-even revenue": "درآمد سر‌به‌سر طرح ۱",
    "Plan 1 contribution margin": "حاشیه مشارکت طرح ۱", "Plan 2 break-even units": "واحد سر‌به‌سر طرح ۲",
    "Equal-cost volume of the two plans": "حجم هم‌هزینگی دو طرح",
    "Cheaper above that volume": "ارزان‌تر در حجم بالاتر",

    # result values
    "Accept": "پذیرش", "Reject": "رد", "not recovered": "بازگشت نمی‌یابد",
    "continuous": "پیوسته", "Plan 1": "طرح ۱", "Plan 2": "طرح ۲",

    # tables
    "Symbol": "نماد", "Description": "شرح", "Factor": "ضریب", "Applied": "کاربرد", "Result": "نتیجه",
    "Worth over the analysis period": "ارزش در دوره تحلیل", "Incremental analysis": "تحلیل افزایشی",
    "PW": "ارزش فعلی", "AW": "ارزش سالانه", "Comparison": "مقایسه",
    "Delta PW": "تفاوت ارزش فعلی", "Incremental ROR": "نرخ بازده افزایشی",
    "Year": "سال", "Accumulated": "انباشته", "Book value": "ارزش دفتری",
    "Period": "دوره", "Payment": "قسط", "Interest": "بهره", "Balance": "مانده",
    "BTCF": "جریان نقدی پیش از مالیات", "Taxable income": "درآمد مشمول مالیات",
    "Tax": "مالیات", "ATCF": "جریان نقدی پس از مالیات",
    # factor descriptions (shown as tooltips)
    "Single payment compound amount": "مبلغ آتی پرداخت منفرد",
    "Single payment present worth": "ارزش فعلی پرداخت منفرد",
    "Sinking fund": "صندوق استهلاک", "Capital recovery": "بازیافت سرمایه",
    "Uniform series compound amount": "مبلغ آتی سری یکنواخت",
    "Uniform series present worth": "ارزش فعلی سری یکنواخت",
    "Arithmetic gradient present worth": "ارزش فعلی گرادیان حسابی",
    "Arithmetic gradient annual series": "سری سالانه گرادیان حسابی",
    "Geometric gradient present worth": "ارزش فعلی گرادیان هندسی",
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
