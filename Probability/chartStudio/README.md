
# ChartStudio

A minimal PyQt6 desktop app for plotting statistics and engineering
charts: line, bar, scatter, histogram, and box plot.

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Features

- Load sample data, import a CSV (first column = labels, remaining
  columns = numeric series), or type series values manually.
- Five chart kinds: line, bar, scatter, histogram, box plot.
- Per-series summary statistics (count, mean, median, stdev, min, max).
- Custom frameless dark window chrome with drag-to-move title bar.
- Export the current chart as a PNG.

## Structure

- `core/` — data model, CSV import, statistics. No widget imports.
- `ui/` — the Qt window, panels, and themed matplotlib canvas.
- `main.py` — entry point.

## Verified in this environment

Without network access here, PyQt6 itself could not be installed or
run, so the actual window was not visually confirmed. What was
verified directly:

- All files parse with no syntax errors.
- `core/models.py` and `core/engine.py` logic (dataset handling, CSV
  parsing including bad-value handling, summary statistics) was
  exercised directly and produces correct results.
- The matplotlib chart-drawing calls used in `ChartCanvas` (line, bar,
  scatter, histogram, box plot) were run standalone against the real
  matplotlib installed here and render correctly; one API mismatch
  (`boxplot`'s `labels` vs `tick_labels` argument across matplotlib
  versions) was caught this way and fixed with a version-safe fallback.

Not verified here: the actual PyQt6 window opening, the frameless
drag-to-move behavior, button hover states, and overall look on your
machine. Please run it locally and report back if anything looks off.
