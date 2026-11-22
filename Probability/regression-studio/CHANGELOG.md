# Changelog
## 1.1.0

- **Influence tab**: leverage, externally studentized residuals and Cook's distance for every point, a plot (studentized residual vs leverage, marker size = Cook's D) and a table of flagged points.
- **Click to exclude**: click a point in the Fit, Residuals or Influence plot to leave it out and refit immediately; click the hollow marker to restore it. "Exclude selected" and "Restore all" in the Influence tab. A change that would make the fit impossible is rolled back.
- **Robust standard errors (HC3)** option for coefficient tests and confidence intervals.
- **Breusch-Pagan** heteroscedasticity test and a flagged/excluded summary in the report.
- Refactor: `main_window.py` split into `sidebar`, `data_page`, `results_page`, `compare_page` and `influence_page`.
- Fix: model comparison respects excluded rows.

## 1.0.0

- Initial release: data grid, six regression types, dashboard cards, plots, prediction intervals, model comparison, exports.
