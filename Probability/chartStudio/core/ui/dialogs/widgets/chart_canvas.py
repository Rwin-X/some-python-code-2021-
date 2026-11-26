"""Embeds a themed matplotlib figure inside the Qt window."""

from __future__ import annotations

import matplotlib

matplotlib.use("QtAgg")

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from core.models import ChartKind, ChartSpec, Dataset
from ui import style


class ChartCanvas(FigureCanvasQTAgg):
    """A themed matplotlib canvas that renders a ChartSpec over a Dataset."""

    def __init__(self) -> None:
        self.figure = Figure(figsize=(5, 4), dpi=100)
        super().__init__(self.figure)
        self._apply_figure_theme()
        self.axes = self.figure.add_subplot(111)
        self._style_axes(self.axes)

    def render(self, dataset: Dataset, spec: ChartSpec) -> None:
        self.figure.clear()
        self._apply_figure_theme()
        axes = self.figure.add_subplot(111)
        self._style_axes(axes)
        self.axes = axes

        if dataset.is_empty() or not spec.selected_series:
            axes.text(
                0.5,
                0.5,
                "No data selected",
                ha="center",
                va="center",
                color=style.TEXT_TERTIARY,
                transform=axes.transAxes,
            )
            self.draw()
            return

        if spec.kind == ChartKind.LINE:
            self._render_line(axes, dataset, spec)
        elif spec.kind == ChartKind.BAR:
            self._render_bar(axes, dataset, spec)
        elif spec.kind == ChartKind.SCATTER:
            self._render_scatter(axes, dataset, spec)
        elif spec.kind == ChartKind.HISTOGRAM:
            self._render_histogram(axes, dataset, spec)
        elif spec.kind == ChartKind.BOX:
            self._render_box(axes, dataset, spec)

        axes.set_title(spec.title, color=style.TEXT_PRIMARY, fontsize=12)
        axes.set_xlabel(spec.x_label, color=style.TEXT_SECONDARY)
        axes.set_ylabel(spec.y_label, color=style.TEXT_SECONDARY)
        axes.grid(spec.show_grid, color=style.BORDER, linewidth=0.6, alpha=0.6)

        if spec.show_legend and spec.kind in (ChartKind.LINE, ChartKind.BAR, ChartKind.SCATTER):
            legend = axes.legend(frameon=False, labelcolor=style.TEXT_SECONDARY)
            if legend is not None:
                legend.get_frame().set_facecolor(style.BG_ELEVATED)

        self.figure.tight_layout()
        self.draw()

    def _render_line(self, axes, dataset: Dataset, spec: ChartSpec) -> None:
        x_values = range(dataset.row_count())
        for index, name in enumerate(spec.selected_series):
            series = dataset.get_series(name)
            if series is None:
                continue
            color = style.PLOT_LINE_COLORS[index % len(style.PLOT_LINE_COLORS)]
            axes.plot(x_values, series.values, label=name, color=color, linewidth=1.8)
        self._apply_label_ticks(axes, dataset)

    def _render_bar(self, axes, dataset: Dataset, spec: ChartSpec) -> None:
        import numpy as np

        count = len(spec.selected_series)
        row_count = dataset.row_count()
        x_positions = np.arange(row_count)
        width = 0.8 / max(count, 1)

        for index, name in enumerate(spec.selected_series):
            series = dataset.get_series(name)
            if series is None:
                continue
            color = style.PLOT_LINE_COLORS[index % len(style.PLOT_LINE_COLORS)]
            offset = (index - (count - 1) / 2) * width
            axes.bar(x_positions + offset, series.values, width=width, label=name, color=color)

        axes.set_xticks(list(x_positions))
        self._apply_label_ticks(axes, dataset)

    def _render_scatter(self, axes, dataset: Dataset, spec: ChartSpec) -> None:
        names = spec.selected_series
        if len(names) >= 2:
            x_series = dataset.get_series(names[0])
            y_series = dataset.get_series(names[1])
            if x_series and y_series:
                axes.scatter(
                    x_series.values,
                    y_series.values,
                    color=style.PLOT_LINE_COLORS[0],
                    alpha=0.85,
                )
                axes.set_xlabel(spec.x_label or names[0], color=style.TEXT_SECONDARY)
                axes.set_ylabel(spec.y_label or names[1], color=style.TEXT_SECONDARY)
        elif len(names) == 1:
            series = dataset.get_series(names[0])
            if series is not None:
                axes.scatter(
                    range(len(series.values)),
                    series.values,
                    color=style.PLOT_LINE_COLORS[0],
                    alpha=0.85,
                    label=names[0],
                )

    def _render_histogram(self, axes, dataset: Dataset, spec: ChartSpec) -> None:
        for index, name in enumerate(spec.selected_series):
            series = dataset.get_series(name)
            if series is None:
                continue
            color = style.PLOT_LINE_COLORS[index % len(style.PLOT_LINE_COLORS)]
            axes.hist(
                series.values,
                bins=max(spec.bins, 1),
                color=color,
                alpha=0.75 if len(spec.selected_series) > 1 else 0.9,
                label=name,
                edgecolor=style.BG_BASE,
            )

    def _render_box(self, axes, dataset: Dataset, spec: ChartSpec) -> None:
        data = []
        labels = []
        for name in spec.selected_series:
            series = dataset.get_series(name)
            if series is None:
                continue
            data.append([v for v in series.values if v == v])
            labels.append(name)

        if not data:
            return

        try:
            box = axes.boxplot(data, tick_labels=labels, patch_artist=True)
        except TypeError:
            # Older Matplotlib (< 3.9) uses the "labels" keyword instead.
            box = axes.boxplot(data, labels=labels, patch_artist=True)
        for index, patch in enumerate(box["boxes"]):
            color = style.PLOT_LINE_COLORS[index % len(style.PLOT_LINE_COLORS)]
            patch.set_facecolor(color)
            patch.set_alpha(0.55)
        for element in ("whiskers", "caps", "medians"):
            for line in box[element]:
                line.set_color(style.TEXT_PRIMARY)

    def _apply_label_ticks(self, axes, dataset: Dataset) -> None:
        if dataset.labels and len(dataset.labels) == dataset.row_count():
            step = max(len(dataset.labels) // 10, 1)
            positions = list(range(0, len(dataset.labels), step))
            axes.set_xticks(positions)
            axes.set_xticklabels(
                [dataset.labels[i] for i in positions], rotation=0, color=style.TEXT_SECONDARY
            )

    def _apply_figure_theme(self) -> None:
        self.figure.patch.set_facecolor(style.BG_BASE)

    def _style_axes(self, axes) -> None:
        axes.set_facecolor(style.BG_BASE)
        for spine in axes.spines.values():
            spine.set_color(style.BORDER)
        axes.tick_params(colors=style.TEXT_SECONDARY)
