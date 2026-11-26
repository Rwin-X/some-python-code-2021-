"""Plain data models for ChartStudio. No widget imports here."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ChartKind(str, Enum):
    LINE = "line"
    BAR = "bar"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    BOX = "box"


@dataclass
class Series:
    """One named column of numeric values."""

    name: str
    values: list[float] = field(default_factory=list)


@dataclass
class Dataset:
    """A small in-memory table: one optional label column plus series."""

    labels: list[str] = field(default_factory=list)
    series: list[Series] = field(default_factory=list)

    def series_names(self) -> list[str]:
        return [s.name for s in self.series]

    def get_series(self, name: str) -> Series | None:
        for s in self.series:
            if s.name == name:
                return s
        return None

    def add_series(self, name: str, values: list[float]) -> None:
        self.series.append(Series(name=name, values=values))

    def remove_series(self, name: str) -> None:
        self.series = [s for s in self.series if s.name != name]

    def rename_series(self, old_name: str, new_name: str) -> None:
        s = self.get_series(old_name)
        if s is not None:
            s.name = new_name

    def row_count(self) -> int:
        if not self.series:
            return len(self.labels)
        return max(len(s.values) for s in self.series)

    def is_empty(self) -> bool:
        return not self.series or all(len(s.values) == 0 for s in self.series)


@dataclass
class ChartSpec:
    """Everything needed to render one chart from a Dataset."""

    kind: ChartKind = ChartKind.LINE
    title: str = ""
    x_label: str = ""
    y_label: str = ""
    selected_series: list[str] = field(default_factory=list)
    bins: int = 10  # histogram only
    show_grid: bool = True
    show_legend: bool = True
