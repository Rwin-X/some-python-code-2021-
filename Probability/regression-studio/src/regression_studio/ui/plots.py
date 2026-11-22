"""Matplotlib canvases styled to match the application palette.

Canvases that show individual observations are clickable: a click near a
point emits point_clicked(table_row_index) so the window can exclude or
restore that row.
"""

from __future__ import annotations

import math
import os

os.environ.setdefault("QT_API", "pyqt6")

import numpy as np  # noqa: E402
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from PyQt6.QtCore import pyqtSignal  # noqa: E402

from regression_studio.core import stats  # noqa: E402
from regression_studio.core.diagnostics import OUTLIER_LIMIT  # noqa: E402
from regression_studio.core.engine import curve_grid, excluded_fitted, predict  # noqa: E402
from regression_studio.core.models import FitResult  # noqa: E402

from . import style  # noqa: E402

PICK_RADIUS_PX = 12.0


def _style_axis(ax) -> None:
    ax.set_facecolor(style.BG_SUNKEN)
    for spine in ax.spines.values():
        spine.set_color(style.BORDER)
    ax.tick_params(colors=style.TEXT_SECONDARY, labelsize=9)
    ax.xaxis.label.set_color(style.TEXT_SECONDARY)
    ax.yaxis.label.set_color(style.TEXT_SECONDARY)
    ax.grid(True, color=style.BORDER, linewidth=0.6, alpha=0.8)
    ax.set_axisbelow(True)


def _title(ax, text: str) -> None:
    ax.set_title(text, color=style.TEXT_PRIMARY, fontsize=11, loc="left")


def _legend(ax) -> None:
    ax.legend(
        facecolor=style.BG_ELEVATED,
        edgecolor=style.BORDER,
        labelcolor=style.TEXT_SECONDARY,
        fontsize=9,
        loc="best",
    )


def _excluded_markers(ax, xs: np.ndarray, ys: np.ndarray) -> None:
    ax.scatter(xs, ys, s=34, facecolors="none", edgecolors=style.DANGER, linewidths=1.4,
               label=f"Excluded ({xs.size})", zorder=3)


class _PlotBase(FigureCanvasQTAgg):
    point_clicked = pyqtSignal(int)  # table row index (0-based)

    def __init__(self, ncols: int = 1, clickable: bool = False) -> None:
        figure = Figure(figsize=(6, 4), dpi=100, facecolor=style.BG_BASE, layout="constrained")
        super().__init__(figure)
        self._axes = list(figure.subplots(1, ncols, squeeze=False)[0])
        self._picks: list[tuple] = []
        self.setMinimumSize(240, 160)
        if clickable:
            self.mpl_connect("button_press_event", self._on_click)
            self.setToolTip("Click a point to exclude it from the fit; click a hollow point to restore it.")
        self.show_empty()

    def _reset(self) -> list:
        self._picks = []
        for ax in self._axes:
            ax.clear()
            _style_axis(ax)
        return self._axes

    def _register(self, ax, xs, ys, rows) -> None:
        """Make points clickable; `rows` are their table row indices."""
        if len(rows):
            self._picks.append((ax, np.asarray(xs, float), np.asarray(ys, float), np.asarray(rows)))

    def _on_click(self, event) -> None:
        if event.button != 1 or event.inaxes is None:
            return
        best_distance, best_row = PICK_RADIUS_PX, None
        for ax, xs, ys, rows in self._picks:
            if ax is not event.inaxes:
                continue
            ok = np.isfinite(xs) & np.isfinite(ys)
            if not ok.any():
                continue
            pixels = ax.transData.transform(np.column_stack([xs[ok], ys[ok]]))
            distance = np.hypot(pixels[:, 0] - event.x, pixels[:, 1] - event.y)
            i = int(np.argmin(distance))
            if distance[i] <= best_distance:
                best_distance, best_row = float(distance[i]), int(rows[ok][i])
        if best_row is not None:
            self.point_clicked.emit(best_row)

    def show_empty(self) -> None:
        for ax in self._reset():
            ax.set_xticks([])
            ax.set_yticks([])
        self._axes[0].text(
            0.5, 0.5, "Run a regression to see this plot.",
            transform=self._axes[0].transAxes, ha="center", va="center",
            color=style.TEXT_TERTIARY, fontsize=11,
        )
        self.draw_idle()


class FitPlot(_PlotBase):
    def __init__(self) -> None:
        super().__init__(clickable=True)

    def render(self, r: FitResult) -> None:
        ax = self._reset()[0]
        pct = f"{r.level * 100:g}%"
        has_excluded = r.rows_excluded.size > 0
        if r.x.shape[1] == 1:
            grid = curve_grid(r)
            pred = predict(r, grid[:, None])
            ax.scatter(r.x[:, 0], r.y, s=22, color=style.POINT, alpha=0.85,
                       linewidths=0, label="Observed", zorder=3)
            self._register(ax, r.x[:, 0], r.y, r.row_index)
            if has_excluded:
                _excluded_markers(ax, r.x_excluded[:, 0], r.y_excluded)
                self._register(ax, r.x_excluded[:, 0], r.y_excluded, r.rows_excluded)
            ax.fill_between(grid, pred.ci_low, pred.ci_high, color=style.ACCENT,
                            alpha=0.15, linewidth=0, label=f"{pct} confidence band")
            ax.plot(grid, pred.yhat, color=style.ACCENT, linewidth=2,
                    label=f"Fit (R\u00b2 = {r.r2:.3f})", zorder=4)
            lo = min(float(r.y.min()), float(pred.yhat.min()))
            hi = max(float(r.y.max()), float(pred.yhat.max()))
            if has_excluded:
                lo, hi = min(lo, float(r.y_excluded.min())), max(hi, float(r.y_excluded.max()))
            pad = 0.08 * ((hi - lo) or 1.0)
            ax.set_ylim(lo - pad, hi + pad)
            ax.set_xlabel(r.spec.x_cols[0])
            ax.set_ylabel(r.spec.y_col)
            _title(ax, "Data and fitted model")
        else:
            lo = float(min(r.y.min(), r.fitted.min()))
            hi = float(max(r.y.max(), r.fitted.max()))
            ax.plot([lo, hi], [lo, hi], color=style.ACCENT, linewidth=2,
                    label=f"Perfect fit (R\u00b2 = {r.r2:.3f})", zorder=4)
            ax.scatter(r.fitted, r.y, s=22, color=style.POINT, alpha=0.85,
                       linewidths=0, label="Observations", zorder=3)
            self._register(ax, r.fitted, r.y, r.row_index)
            if has_excluded:
                fitted_ex = excluded_fitted(r)
                ok = np.isfinite(fitted_ex)
                if ok.any():
                    _excluded_markers(ax, fitted_ex[ok], r.y_excluded[ok])
                    self._register(ax, fitted_ex[ok], r.y_excluded[ok], r.rows_excluded[ok])
            ax.set_xlabel(f"Predicted {r.spec.y_col}")
            ax.set_ylabel(f"Observed {r.spec.y_col}")
            _title(ax, "Observed vs predicted")
        _legend(ax)
        self.draw_idle()


class ResidualPlot(_PlotBase):
    def __init__(self) -> None:
        super().__init__(clickable=True)

    def render(self, r: FitResult) -> None:
        ax = self._reset()[0]
        ax.axhline(0.0, color=style.TEXT_TERTIARY, linewidth=1, linestyle="--")
        ax.scatter(r.fitted, r.residuals, s=22, color=style.POINT, alpha=0.85,
                   linewidths=0, zorder=3)
        self._register(ax, r.fitted, r.residuals, r.row_index)
        if r.rows_excluded.size:
            fitted_ex = excluded_fitted(r)
            ok = np.isfinite(fitted_ex)
            if ok.any():
                resid_ex = r.y_excluded[ok] - fitted_ex[ok]
                _excluded_markers(ax, fitted_ex[ok], resid_ex)
                self._register(ax, fitted_ex[ok], resid_ex, r.rows_excluded[ok])
                _legend(ax)
        ax.set_xlabel("Fitted values")
        ax.set_ylabel("Residuals")
        _title(ax, "Residuals vs fitted")
        self.draw_idle()


class DiagnosticsPlot(_PlotBase):
    def __init__(self) -> None:
        super().__init__(ncols=2)

    def show_empty(self) -> None:
        super().show_empty()
        self._axes[1].set_visible(False)

    def render(self, r: FitResult) -> None:
        hist_ax, qq_ax = self._reset()
        self._axes[1].set_visible(True)
        bins = min(40, max(5, int(math.sqrt(r.n)) + 1))
        hist_ax.hist(r.residuals, bins=bins, color=style.ACCENT, alpha=0.7,
                     edgecolor=style.BG_SUNKEN)
        hist_ax.set_xlabel("Residual")
        hist_ax.set_ylabel("Count")
        _title(hist_ax, "Residual distribution")

        slope, intercept = stats.qq_line(r.qq_theory, r.qq_sample)
        qq_ax.scatter(r.qq_theory, r.qq_sample, s=22, color=style.POINT, alpha=0.85,
                      linewidths=0, zorder=3)
        span = np.array([r.qq_theory.min(), r.qq_theory.max()])
        qq_ax.plot(span, slope * span + intercept, color=style.ACCENT, linewidth=2, zorder=4)
        qq_ax.set_xlabel("Theoretical quantiles")
        qq_ax.set_ylabel("Residual quantiles")
        _title(qq_ax, "Normal Q-Q")
        self.draw_idle()


class InfluencePlot(_PlotBase):
    """Studentized residual vs leverage; marker area grows with Cook's distance."""

    def __init__(self) -> None:
        super().__init__(clickable=True)

    def render(self, r: FitResult) -> None:
        ax = self._reset()[0]
        n, p = r.n, len(r.coef)
        flagged = np.array([bool(f) for f in r.flags])
        top = float(np.nanmax(r.cooks)) if np.isfinite(r.cooks).any() else 0.0
        scale = np.where(np.isfinite(r.cooks), r.cooks / top, 0.0) if top > 0 else np.zeros(n)
        sizes = 18.0 + 200.0 * np.clip(scale, 0.0, 1.0)
        ax.axhline(OUTLIER_LIMIT, color=style.TEXT_TERTIARY, linewidth=1, linestyle="--")
        ax.axhline(-OUTLIER_LIMIT, color=style.TEXT_TERTIARY, linewidth=1, linestyle="--")
        ax.axvline(2.0 * p / n, color=style.TEXT_TERTIARY, linewidth=1, linestyle="--")
        ax.scatter(r.leverage[~flagged], r.studentized[~flagged], s=sizes[~flagged],
                   color=style.POINT, alpha=0.8, linewidths=0, zorder=3)
        ax.scatter(r.leverage[flagged], r.studentized[flagged], s=sizes[flagged],
                   color=style.ACCENT, alpha=0.9, linewidths=0, zorder=4)
        self._register(ax, r.leverage, r.studentized, r.row_index)
        ax.set_xlabel("Leverage")
        ax.set_ylabel("Studentized residual")
        _title(ax, "Influence (marker size = Cook's D)")
        self.draw_idle()
