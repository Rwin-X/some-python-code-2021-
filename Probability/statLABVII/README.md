<div align="center">

```text
 ███████╗████████╗ █████╗ ████████╗    ██╗      █████╗ ██████╗
 ██╔════╝╚══██╔══╝██╔══██╗╚══██╔══╝    ██║     ██╔══██╗██╔══██╗
 ███████╗   ██║   ███████║   ██║       ██║     ███████║██████╔╝
 ╚════██║   ██║   ██╔══██║   ██║       ██║     ██╔══██║██╔══██╗
 ███████║   ██║   ██║  ██║   ██║       ███████╗██║  ██║██████╔╝
 ╚══════╝   ╚═╝   ╚═╝  ╚═╝   ╚═╝       ╚══════╝╚═╝  ╚═╝╚═════╝
```

**Engineering statistics & probability workbench: a single-file, offline desktop app written in Python.**

![Python](https://img.shields.io/badge/python-3.9%2B-2fd9ff?style=flat-square&labelColor=0a0e0d)
![GUI](https://img.shields.io/badge/GUI-tkinter-39ff9c?style=flat-square&labelColor=0a0e0d)
![Engine](https://img.shields.io/badge/engine-NumPy%20%C2%B7%20SciPy%20%C2%B7%20pandas-39ff9c?style=flat-square&labelColor=0a0e0d)
![Plots](https://img.shields.io/badge/plots-Matplotlib-2fd9ff?style=flat-square&labelColor=0a0e0d)
![Offline](https://img.shields.io/badge/runs-100%25%20offline-667a76?style=flat-square&labelColor=0a0e0d)
![License](https://img.shields.io/badge/license-MIT-667a76?style=flat-square&labelColor=0a0e0d)

[Features](#features) ·
[Quick start](#quick-start) ·
[Reference](#feature-reference) ·
[Methods](#methods--conventions) ·
[Library use](#using-the-engine-as-a-library) ·
[Validation](#validation) ·
[Limitations](#limitations--assumptions)

</div>

---

## Overview

**STAT LAB** is a desktop workbench for the statistics and probability that engineering courses and day-to-day
quality work actually need: descriptive statistics, frequency tables, normality and outlier diagnostics,
distribution fitting, hypothesis tests, correlation and regression, a probability calculator, statistical process
control, Weibull reliability analysis, resampling, and a library of 26 textbook-style calculators.

Load a CSV / Excel / JSON file (or paste numbers), pick a variable, and every tab updates. Results are shown as
copyable tables and plain-text reports with explicit hypotheses, test statistics, critical values, p-values and
decisions at your chosen significance level α.

- **One file, no build step.** `stat_lab.py` is the whole application.
- **Offline.** No network access, no telemetry, nothing leaves your machine.
- **Transparent.** Every number is computed with documented formulas on top of NumPy / SciPy, and the engine
  can be imported without opening a window (see [Using the engine as a library](#using-the-engine-as-a-library)).
- **Dark, high-density UI** (phosphor green / cyan, monospace) with matching dark Matplotlib figures.


## Features

| Area | What you get |
|---|---|
| **Input** | CSV, TSV, TXT, DAT, XLSX / XLSM (XLS and ODS with optional extras), JSON, or pasted text; automatic delimiter, header and decimal-comma detection |
| **Descriptive statistics** | 50+ statistics: location, spread, 9 quantile definitions, textbook quartile rules, skewness / kurtosis in several conventions, confidence, prediction and tolerance intervals |
| **Frequency analysis** | Class rules (Sturges, Scott, Freedman-Diaconis, Doane, Rice, sqrt, Stone, custom bins or width, discrete), relative / cumulative frequency, density, stem-and-leaf display |
| **Diagnostics** | Shapiro-Wilk, D'Agostino-Pearson, Anderson-Darling, Jarque-Bera, Lilliefors; Tukey fences, z-score, modified z, Grubbs |
| **Distribution fitting** | MLE for 10 families ranked by AIC / BIC with KS statistic |
| **Hypothesis tests** | 19 parametric and non-parametric tests with critical values, CIs and effect sizes |
| **Correlation & regression** | Pearson / Spearman / Kendall matrices with p-values, covariance, simple regression with ANOVA, CI and prediction intervals |
| **Probability** | 15 distributions (continuous and discrete), tails, intervals, quantiles, empirical probabilities, parameter estimation from data |
| **SPC & reliability** | I-MR, X̄-R, X̄-S charts, Nelson rules, process capability, Weibull MLE with censoring, exponential MTBF |
| **Advanced** | Multiple / polynomial regression with influence diagnostics, bootstrap (BCa), permutation test, CLT simulation |
| **Calculators** | 26 calculators: proportions, χ², summary-data tests, power and sample size, Bayes, combinatorics, system reliability |
| **Transform** | Safe expression columns, 14 transforms (Box-Cox, Yeo-Johnson, z-score, ...), cleaning, filtering, full undo |
| **Output** | Copy any table, save figures (PNG / SVG / PDF), export all-column statistics (CSV / XLSX), export a full text report |


Open a file directly from the command line:

```bash
python stat_lab.py sample_data.csv
```

<details>
<summary><b>Platform notes</b></summary>

- **Linux (Debian / Ubuntu):** `tkinter` is a separate package: `sudo apt install python3-tk`.
- **Fedora:** `sudo dnf install python3-tkinter`.
- **Windows / macOS:** `tkinter` ships with the python.org installers.
- **Legacy formats:** `.xls` needs `pip install xlrd`; `.ods` needs `pip install odfpy`. `.xlsx` is handled by `openpyxl`.
- **Fonts:** the UI prefers *JetBrains Mono*, then Cascadia Mono, Consolas, DejaVu Sans Mono, Menlo, Liberation Mono, Courier New.
- **Headless machines:** run under a virtual display, e.g. `xvfb-run python stat_lab.py data.csv`.

</details>

**Dependencies** (`requirements.txt`): `numpy`, `scipy`, `pandas`, `matplotlib`, `openpyxl`.
Developed and smoke-tested on Python 3.12 (Linux) with NumPy 2.5, SciPy 1.18, pandas 3.0 and Matplotlib 3.11.
The APIs used imply roughly NumPy ≥ 1.22, SciPy ≥ 1.11, pandas ≥ 1.5 and Matplotlib ≥ 3.6; older combinations are
untested.

## Quick start

1. **Load data** with `Ctrl+O`, or paste numbers into the **DATA** tab and press *Use this data*.
2. **Choose variables** in the top bar: **X** is the variable analysed by most tabs, **Y** is the second variable
   for two-sample tests, regression, scatter plots, paired analyses and the Weibull / regression tabs.
3. **Set the global options** (press Enter to apply): significance level **α** (the confidence level is `1 − α`),
   **trim %**, **quantile method**, and the number of displayed **digits**.
4. **Explore the tabs.** Descriptive, frequency, diagnostics and the ALL COLS tab update automatically; tests,
   regression, SPC, Weibull, simulations and calculators run on demand.
5. **Export** with `Ctrl+S` (full text report), right-click / `Ctrl+C` on any table, or the *Save image* button.

A small demo dataset is included: [`sample_data.csv`](sample_data.csv) has `force_N`, `displacement_mm`,
`life_h` (Weibull-like lifetimes with one missing value) and `failed` (1 = failure, 0 = suspended).

### Accepted input

| Rule | Behaviour |
|---|---|
| File types | `.csv .tsv .txt .dat .xlsx .xlsm .xls .ods .json` |
| Delimiters | `;`, tab, `\|`, `,`, or whitespace, detected automatically (ragged rows are padded) |
| Header row | `auto` (a first row without any number is treated as header), `yes`, or `no` |
| Decimal mark | `auto`, `.`, or `,` (so `1,5;2,5` is read correctly) |
| Missing values | Blank cells and non-numeric entries in a numeric column become missing; counted and reported |
| Non-numeric columns | Ignored, and listed in the DATA tab |
| Comments | Lines starting with `#` are skipped in text files |
| Encodings | UTF-8 (with BOM), UTF-16, Windows-1256, Latin-1 |
| Excel | Multi-sheet workbooks open a sheet picker |
| JSON | A list of numbers, an object of equal-length lists, or records |
| One line of numbers | `12, 11.5, 13` pasted on a single line becomes one column |

## Feature reference

### DATA and TRANSFORM

- Preview of the first 500 rows; all rows are analysed.
- **Expression columns:** `force_N / displacement_mm`, `where(x > 50, 1, 0)`, `sqrt(x) * 2 + 1`, `cumsum(x)`.
  Column names are variables (or `col["name with spaces"]`), `x` is the selected X, `row` is the row number.
- **Transforms:** z-score, min-max, centre, ln, log10, square root, square, reciprocal, **Box-Cox**,
  **Yeo-Johnson** (λ is reported), rank, cumulative sum, first difference, moving average (window *k*).
- **Cleaning:** drop rows with missing values, fill with mean / median, set Tukey outliers to missing, sort,
  filter rows by an expression, delete a column.
- **Undo** (30 levels), **Reset to original**, **Save data** to CSV / XLSX.

### DESCRIPTIVE

Statistic groups, all with 6 significant digits by default (adjustable):

| Group | Statistics |
|---|---|
| Size | n, missing, Σx, Σx², Sxx |
| Location | mean, median, mode(s), trimmed mean, geometric, harmonic, midrange |
| Spread | min, max, range, variance and standard deviation (sample **and** population), SEM, CV, mean absolute deviation, MAD, scaled MAD (1.4826·MAD), IQR |
| Quantiles | Q1 / Q2 / Q3 in the chosen method, median-of-halves quartiles, Tukey hinges, P1 P5 P10 P90 P95 P99 |
| Shape | skewness *g₁* and *G₁*, excess kurtosis *g₂* and *G₂*, Pearson *b₂*, Pearson 2nd and Bowley skewness, standard errors of skewness and kurtosis |
| Confidence | *t* critical value, margin of error, CI for μ (t), CI for σ² and σ (χ²), prediction interval for one new observation, 95 % normal tolerance interval |
| Outliers | Tukey fences, counts beyond 1.5×IQR and 3×IQR, count with \|z\| > 3 |

### FREQUENCY

Frequency table with class midpoints, frequency, relative and cumulative frequency, and density. Class rules:
`sturges · auto · fd · scott · doane · rice · sqrt · stone`, *number of bins*, *class width*, or *discrete
(unique values)*. Classes are half-open `[a, b)` with the last class closed. A **stem-and-leaf** display (with
automatic leaf unit, split stems and a key) is generated alongside.

### PLOTS

Histogram + KDE + normal fit · histogram + best fitted PDFs · box plot · box plots of all columns · normal Q-Q ·
ECDF with DKW band · run sequence (x̄ ± ks) · scatter + regression with CI and prediction bands · residuals vs
fitted · correlation heat map · autocorrelation (ACF, Ljung-Box) · lag plot · P-P plot · means ± CI · scatter
matrix · histogram grid. Save as PNG, SVG or PDF; the Matplotlib toolbar gives zoom and pan.

### DIAGNOSTICS

- **Normality (H₀: normal):** Shapiro-Wilk, D'Agostino-Pearson K², Anderson-Darling (Stephens p-value
  approximation), Jarque-Bera, Lilliefors (Monte-Carlo p-value). Each row shows the decision at α.
- **Outliers:** Tukey 1.5×IQR and 3×IQR fences, z-score, modified z-score (Iglewicz-Hoaglin), Grubbs test.
  Flagged observations are reported with their **data row number**.

### DIST. FIT

Maximum-likelihood fits of Normal, Lognormal, Exponential, Gamma, Weibull, Rayleigh, Uniform, Logistic,
Laplace and Gumbel (max), with log-likelihood, AIC, ΔAIC, BIC and the Kolmogorov-Smirnov statistic. Families with
positive support are fitted with location fixed at 0 and are skipped when the data violate their support.

### TESTS (19)

| Family | Tests |
|---|---|
| Mean, one sample | One-sample *t*; one-sample *z* (σ known); Wilcoxon signed-rank; sign test |
| Mean, two samples | Welch *t*; pooled *t*; two-sample *z* (σ known); paired *t*; Wilcoxon (paired); Mann-Whitney U; Kolmogorov-Smirnov (two samples) |
| Variance | χ² test for one variance; *F*-test for two variances; Levene / Brown-Forsythe; Bartlett |
| Several groups | One-way ANOVA (with Levene check and η²); Kruskal-Wallis; Tukey HSD post-hoc |
| Randomness | Runs test about the median |

Every report states H₀ / H₁ (two-sided, less or greater), the statistic and degrees of freedom, critical value(s),
a confidence interval for the tested parameter, an effect size where defined (Cohen's *d*, η²), and a decision.

### CORR & REGR

Pearson / Spearman / Kendall correlation matrices with p-values, the covariance matrix, and for the chosen X-Y
pair: correlation with a Fisher-z CI, Spearman ρ, Kendall τ, and **simple linear regression** (coefficients with
SE, *t*, p and CI; ANOVA table; R², adjusted R², residual standard error; Shapiro-Wilk on residuals; prediction at
x₀ with a CI for the mean response and a prediction interval, with an extrapolation warning).

### PROB. CALC

Normal · Student *t* · χ² · *F* · Exponential · Uniform · Gamma · Weibull · Lognormal · Beta · Binomial ·
Poisson · Geometric · Negative binomial · Hypergeometric. For a point *x*, interval [*a*, *b*] and probability *p* it
returns the PDF / PMF, CDF, both tails, the interval probability, quantiles (lower and upper tail) and central
moments, with a shaded PDF / PMF and CDF figure. **Estimate parameters from X** fills the parameters from the data
and sets sensible queries. Empirical probabilities and quantiles of the loaded sample are shown beside the
theoretical ones.

### SPC & RELIAB.

**Control charts and capability**

- I-MR (σ̂ = MR̄ / d₂), X̄-R and X̄-S, with subgroups taken as consecutive blocks of X **or** each data row across
  all columns.
- Nelson rules 1, 2, 3, 5 and 6 on the first chart; limit violations on the range / S / MR chart; flagged points
  highlighted.
- With LSL / USL / target: **Cp, Cpu, Cpl, Cpk, Pp, Ppu, Ppl, Ppk, Cpm** with confidence intervals, observed and
  expected ppm (overall and within), yield, bench Z, and a normality warning.

**Weibull / reliability**

- Maximum-likelihood Weibull fit with **right-censored (suspended) units** via a censoring column
  (1 = failure, 0 = censored).
- CIs for β, η, MTTF and B1 / B5 / B10 lives; R(*t*), F(*t*) and hazard at a mission time with a CI for R(*t*)
  (delta method).
- Weibull probability plot (Johnson adjusted ranks, Bernard median-rank plotting positions), reliability, hazard and
  density plots; an exponential MTBF comparison with χ² confidence limits.

### ADVANCED

- **Multiple / polynomial regression:** any set of predictors, polynomial degree 1-6, optional centring.
  Coefficient table with SE, *t*, p, CI, **VIF** and standardised β; R², adjusted R², predicted R² (PRESS), AIC,
  BIC, Durbin-Watson; ANOVA table; residual normality; leverage, studentised residuals and **Cook's distance** with
  flagged rows; prediction with CI and PI; four diagnostic plots.
- **Bootstrap:** mean, median, standard deviation, variance, trimmed mean, IQR, CV, skewness, correlation, paired
  mean difference, independent mean difference; BCa, percentile or basic intervals; bootstrap SE and bias.
- **Permutation test** for a difference in means (no normality assumption).
- **Central limit theorem demo** for any of the 15 probability distributions.

### CALCULATORS (26)

| Category | Calculators |
|---|---|
| **Proportions & counts** | Proportion CI (Wald, Wilson, Agresti-Coull, Clopper-Pearson, Jeffreys) · one-proportion test (exact and z) · two-proportion test (z, Fisher, Newcombe CI, RR, OR) · χ² goodness-of-fit · χ² independence with Cramér's V and residuals · Poisson rate |
| **Means & variances (summary data)** | One-sample *t* · two-sample *t* (Welch / pooled) · CI with σ known · one-way ANOVA from group summaries · correlation test (*t* and Fisher z) · tolerance & prediction interval. Fields can be filled from X / Y with one click. |
| **Sample size & power** | *n* for a mean · *n* for a proportion · power / *n* for the *t*-test (non-central *t*) · power / *n* for two proportions |
| **Probability rules** | Combinatorics · Bayes' theorem · two events A, B · custom discrete distribution · Chebyshev & Markov · linear combination aX + bY · sampling distribution of X̄ (with finite-population correction) · normal approximation to the binomial |
| **Reliability** | Series / parallel / *k*-out-of-*n* systems · exponential model (MTBF) |

### ALL COLS

Descriptive statistics of every numeric column side by side, exportable to CSV or XLSX.

### Keyboard & mouse

| Action | Shortcut |
|---|---|
| Open file | `Ctrl+O` |
| Export text report | `Ctrl+S` |
| Recompute everything | `F5` |
| Copy selected table rows (with header) | `Ctrl+C` or right-click |
| Select all rows in a table | `Ctrl+A` |

## Methods & conventions

<details>
<summary><b>Quantiles, shape and intervals</b></summary>

- **Quantile methods** (`numpy.quantile`): `linear` (R-7, Excel `QUARTILE.INC`), `weibull` (R-6, Minitab / Excel
  `QUARTILE.EXC`), `hazen`, `median_unbiased`, `normal_unbiased`, `lower`, `higher`, `midpoint`, `nearest`.
  The two textbook rules (median of halves with the median excluded or included) are always shown too.
- **Skewness / kurtosis:** *g₁*, *g₂* are population (biased) moments; *G₁*, *G₂* are the sample-adjusted versions
  used by Excel `SKEW` / `KURT`; *b₂* is Pearson kurtosis (normal = 3).
- **Mean CI:** x̄ ± t₁₋α/₂,ₙ₋₁ · s/√n. **Variance CI:** (n−1)s² / χ²₁₋α/₂ to (n−1)s² / χ²α/₂.
- **Prediction interval:** x̄ ± t · s · √(1 + 1/n).
- **Tolerance interval:** two-sided normal interval x̄ ± k·s with Howe's approximation
  k = z₍₁₊ₚ₎/₂ · √[(n−1)(1 + 1/n) / χ²₁₋γ,ₙ₋₁] (95 % coverage; confidence 1 − α).
- **Sums** use `math.fsum`; variances use a two-pass algorithm.

</details>

<details>
<summary><b>Normality and outliers</b></summary>

- **Anderson-Darling:** A² is computed from the standardised order statistics with `logcdf` / `logsf`; the p-value
  uses the Stephens (1986) piecewise approximation on A*² = A²(1 + 0.75/n + 2.25/n²).
- **Lilliefors:** KS statistic with estimated μ and σ; p-value from Monte-Carlo simulation (seeded, 200 to 2000
  replicates depending on n).
- **Grubbs (two-sided):** G = max|xᵢ − x̄| / s against G_crit = (n−1)/√n · √[t² / (n − 2 + t²)] with
  t = t₁₋α/(2n), n−2.
- **Modified z:** Mᵢ = 0.6745 (xᵢ − median) / MAD, flagged at |M| > 3.5.

</details>

<details>
<summary><b>Control charts and capability</b></summary>

- Constants d₂(n), d₃(n) for n = 2..25 come from numerical integration of the range distribution of normal samples
  (5 decimals); c₄(n) is the closed-form gamma expression.
- **X̄-R:** limits x̿ ± 3R̄/(d₂√n); R chart D₃ = max(0, 1 − 3d₃/d₂), D₄ = 1 + 3d₃/d₂.
  **X̄-S:** x̿ ± 3S̄/(c₄√n); B₃, B₄ from c₄. **I-MR:** σ̂ = MR̄/d₂(2), MR upper limit D₄·MR̄.
- **Capability:** Cp, Cpk use the *within* σ̂ from the chart; Pp, Ppk use the overall sample standard deviation.
  Cp CI via χ²; Cpk / Ppk CI via the Bissell approximation. ppm assume a normal distribution.

</details>

<details>
<summary><b>Weibull and reliability</b></summary>

- Log-likelihood with right censoring: Σ_fail[ln β − β ln η + (β−1) ln t] − Σ_all (t/η)^β, maximised over
  (ln β, ln η) with Nelder-Mead; covariance from the inverse numerical Hessian.
- CIs for β, η, MTTF and B_p lives are log-normal (delta method); the CI for R(t) uses
  ln(−ln R) = β(ln t − ln η).
- Plotting positions: Johnson adjusted ranks with Bernard's approximation (i − 0.3)/(n + 0.4).
- Exponential MTBF: failure-terminated (no censoring) uses 2r degrees of freedom on both limits; time-terminated
  uses 2r + 2 for the lower limit.

</details>

<details>
<summary><b>Hypothesis-test conventions</b></summary>

- The alternative is `two-sided`, `less` or `greater`; for χ² and *F* tests the two-sided p-value is
  2·min(CDF, SF) (capped at 1).
- Welch degrees of freedom use Welch-Satterthwaite; one-sided confidence intervals are reported for one-sided tests.
- For two-sample tests X and Y are cleaned independently; **paired** procedures use only rows where both are present.
- ANOVA-type tests treat every numeric column as a group.
- p-values smaller than 1e-12 are displayed as `< 1e-12` and never as exactly 0.

</details>

## Using the engine as a library

All computations are plain functions that do not touch the GUI. Importing `stat_lab` needs `tkinter` to be
installed (Matplotlib's TkAgg backend is selected at import time) but opens no window.

```python
import numpy as np
import stat_lab as S

x = np.random.default_rng(0).normal(50, 5, 100)

# descriptive statistics -> rows of (group, statistic, value, note)
for group, name, value, note in S.describe(x, conf=0.95):
    print(f"{name:<45}{S.fmt(value)}")

# a hypothesis test -> formatted report string
print(S.run_test("One-sample t-test", x, None, 0.05, "two-sided", mu0=50))

# any calculator -> report string
print(S.CALCS["Sample size & power"]["n to estimate a mean"].fn([2.0, 0.5], 0.05))
```

Other entry points: `S.normality_tests`, `S.outlier_report`, `S.fit_distributions`, `S.frequency_table`,
`S.stem_and_leaf`, `S.regression`, `S.multi_regression`, `S.control_chart`, `S.capability`, `S.weibull_report`,
`S.bootstrap_report`, `S.prob_calc`.

## Project layout

`stat_lab.py` is organised in clearly separated sections:

```text
stat_lab.py
├── Theme, number formatting, data loading / parsing
├── Statistics engine ......... describe, frequency, normality, outliers, fitting, tests, regression
├── Extended engine ........... SPC, capability, Weibull, multiple regression, resampling, transforms
├── Calculators ............... CALCS registry  (category -> name -> CalcSpec)
├── GUI mixin (ExtraTabs) ..... transform, SPC / reliability, advanced, calculators, extra plots
└── GUI (StatLab) ............. theme, core tabs, plots, export, entry point
```

**Adding a calculator** takes a function and one registry entry:

```python
def calc_double(v, alpha):                       # v = parsed field values
    return f"2 × {v[0]} = {2 * v[0]}"

CALCS["Probability rules"]["Doubler"] = CalcSpec(
    [F("Number", 21)],                           # (label, default, kind, choices, fill_key)
    "Doubles a number.", calc_double)
```

Field kinds: `f` float · `i` integer · `o` optional float · `s` text · `c` choice · `m` multi-line text.

## Validation

The numerical core was cross-checked against independent references during development:

- descriptive statistics, skewness, confidence intervals, one-sample and Welch *t*, Anderson-Darling (against
  SciPy), χ² independence and goodness-of-fit (against SciPy);
- Clopper-Pearson and Wilson proportion intervals, and the non-central-*t* power results (for example 64 per
  group for a two-sample test and 34 for a one-sample test at d = 0.5, power 0.8), which agree with standard
  power software;
- the Howe tolerance factor (3.38 for n = 10, 95 % / 95 %), control-chart constants against the standard tables,
  and the uncensored Weibull MLE against `scipy.stats.weibull_min.fit`;
- the full GUI (all tabs, 16 plots, 19 tests, 26 calculators, all transforms) was exercised end-to-end under a
  virtual display on Linux.

There is no automated test suite in this repository yet; contributions that add one are welcome.

## Limitations & assumptions

- **Distributional assumptions:** *t*, *z*, ANOVA, tolerance intervals, capability indices and regression
  inference assume approximately normal data / residuals. Use the diagnostics and the non-parametric alternatives
  when that is doubtful.
- **KS p-values in DIST. FIT are optimistic** because parameters are estimated from the same data; rank by AIC / BIC
  and inspect Q-Q plots.
- **Capability indices** are only meaningful for a process in statistical control. The report flags rule
  violations.
- **Weibull** analysis supports right censoring only (no interval or left censoring) and two parameters.
- **Large data:** everything is held in memory. Very large files (millions of rows) will be slow, especially
  distribution fitting and bootstrap runs. Shapiro-Wilk p-values are approximate above n = 5000.
- **Expressions** (TRANSFORM tab) run in a restricted namespace: no attribute access, imports, `open`, `eval`,
  `exec` or `lambda`. They are still evaluated with Python's `eval`, so only use expressions you wrote yourself.
- The interface is **English only** (no right-to-left layout).
- Tested on Linux; Windows and macOS are expected to work but have not been verified.

## Roadmap

Ideas, not promises: two-way ANOVA and design of experiments, time-series models (ARIMA, exponential smoothing),
logistic regression, interval-censored reliability data, an automated test suite, and a packaged installer.

## Contributing

Issues and pull requests are welcome. Please keep engine functions free of GUI code, include a
reference value (textbook, SciPy or R) for any new statistic, and keep the single-file layout unless there is a
strong reason to split it.

## References

- Agresti, A. & Coull, B. (1998). Approximate is better than "exact" for interval estimation of binomial proportions. *The American Statistician*.
- Bissell, A. F. (1990). How reliable is your capability index? *Applied Statistics*.
- Clopper, C. & Pearson, E. (1934). The use of confidence or fiducial limits illustrated in the case of the binomial. *Biometrika*.
- D'Agostino, R. & Stephens, M. (1986). *Goodness-of-Fit Techniques*. Marcel Dekker.
- Grubbs, F. (1969). Procedures for detecting outlying observations in samples. *Technometrics*.
- Howe, W. G. (1969). Two-sided tolerance limits for normal populations. *Journal of the American Statistical Association*.
- Iglewicz, B. & Hoaglin, D. (1993). *How to Detect and Handle Outliers*. ASQC Quality Press.
- Johnson, L. (1964). *The Statistical Treatment of Fatigue Experiments*. Elsevier.
- Lilliefors, H. (1967). On the Kolmogorov-Smirnov test for normality with mean and variance unknown. *JASA*.
- Nelson, L. (1984). The Shewhart control chart: tests for special causes. *Journal of Quality Technology*.
- Newcombe, R. (1998). Interval estimation for the difference between independent proportions. *Statistics in Medicine*.
- Shapiro, S. & Wilk, M. (1965). An analysis of variance test for normality. *Biometrika*.
- Wilson, E. (1927). Probable inference, the law of succession, and statistical inference. *JASA*.


