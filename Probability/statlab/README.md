# StatLab

A PyQt6 desktop application for basic engineering statistics and
probability work: load a dataset, get full descriptive statistics,
explore probability distributions, and run common hypothesis tests —
all with no server, no account, and no internet connection required.

## Features

**Data**
- Load CSV, TSV, TXT, XLSX, or XLS files
- Automatic column classification (numeric vs. categorical)
- Row/column preview table
- File loading runs on a background thread, so the UI never freezes
  on a large file

**Descriptive statistics** (per column)
- Count, missing count, mean, median, mode
- Standard deviation, variance, min, max, range
- Quartiles (Q1/Q3), interquartile range
- Skewness, excess kurtosis
- Standard error of the mean, 95% confidence interval of the mean
- Histogram (numeric) or top-category bar chart (categorical)
- Outlier detection via the 1.5×IQR rule

**Correlation matrix**
- Pearson correlation heatmap across every numeric column at once

**Hypothesis tests**
- Pearson and Spearman correlation between two columns, with a scatter plot
- Simple linear regression (slope, intercept, R², p-value), with fit line
- One-sample t-test
- Two-sample independent t-test (Welch's, unequal variance by default)
- Paired t-test
- Chi-square test of independence, with a contingency-table heatmap and
  a warning if any expected cell count is below 5
- One-way ANOVA, with a box plot by group
- Every test reports its statistic, degrees of freedom, p-value, and a
  plain-language reject/fail-to-reject line at alpha = 0.05

**Probability distributions**
- Normal, Binomial, Poisson, Uniform, Exponential
- Adjustable parameters with live PDF/PMF and CDF plots
- Mean/variance/std-dev readout
- Probability queries: P(a ≤ X ≤ b), P(X ≤ b), P(X ≥ a), and P(X = a)
  for discrete distributions

## Project layout

```
statlab/
├── main.py                        # entry point
├── core/                          # pure logic, no PyQt6.QtWidgets imports
│   ├── models.py                   # dataclasses for results and summaries
│   ├── data_loader.py              # file parsing + column classification
│   ├── descriptive.py              # descriptive statistics
│   ├── distributions.py            # probability distribution math
│   └── inferential.py              # correlation, t-tests, chi-square, ANOVA, regression
└── ui/                             # imports core, never the reverse
    ├── style.py                     # QSS + palette constants
    ├── workers.py                   # QThread worker objects
    ├── main_window.py                # frameless window + tab wiring
    └── widgets/
        ├── title_bar.py              # custom draggable title bar
        ├── window_controls.py        # QPainter-drawn min/max/close glyphs
        ├── chart_canvas.py           # themed matplotlib canvas
        ├── overview_panel.py         # file loading + preview
        ├── descriptive_panel.py      # per-column statistics + histogram
        ├── correlation_matrix_panel.py
        ├── inferential_panel.py      # hypothesis tests
        └── probability_panel.py      # distribution calculator
```

`core/` has no dependency on `ui/` and only touches
`PyQt6.QtCore.pyqtSignal`/`QObject` for the background data-load
worker — it can be unit-tested with no display attached:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/
```

## Running it

```bash
pip install -r requirements.txt
python main.py
```

## Known limitations / what to check on your own machine

This was built and reviewed in a sandboxed environment with no
network access, so **PyQt6 itself could not be installed or actually
launched here** — the code was written and checked carefully against
the PyQt6 API, but it has not been run against a real display. Please
treat the first run as a shakeout:

- Frameless-window dragging and the maximize/restore glyph swap are
  implemented per the standard pattern but should be confirmed on
  your actual window manager (behavior can vary slightly on Linux
  desktops).
- Large files (multi-million-row CSVs) will load in the background
  thread without freezing the UI, but very large files will still use
  a lot of memory since the whole table is held in a pandas
  DataFrame — there's no chunked/streaming mode.
- Chi-square and ANOVA assume the grouping column has a reasonable
  number of distinct categories; a categorical column with hundreds
  of unique values (e.g. a free-text field) will produce a cluttered
  contingency table or box plot rather than failing outright.
- Excel loading depends on `openpyxl`, which is in requirements.txt —
  without it, `.xlsx`/`.xls` loading will raise an error.

## Why these specific design choices

- **Welch's t-test by default** for the two-sample case (unequal
  variance assumed) rather than the pooled-variance Student's t-test,
  since in real engineering data equal variance is an assumption worth
  not taking for granted.
- **1.5×IQR rule** for outlier flagging rather than a z-score cutoff,
  since it doesn't assume normality.
- **Background thread for file loading only.** The statistical
  computations themselves (even on a few hundred thousand rows) are
  fast enough with numpy/scipy that adding thread plumbing for every
  button would add complexity without a real responsiveness benefit;
  file I/O and parsing is the one operation here that can meaningfully
  exceed 50ms on realistic inputs.
