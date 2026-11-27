"""Statistics and data-import logic. Zero PyQt widget imports.

Only PyQt6.QtCore is used here (QObject/pyqtSignal), for emitting
data-changed events to the UI layer without the engine knowing any
widget exists.
"""

from __future__ import annotations

import csv
import statistics
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from core.models import Dataset


class DataEngine(QObject):
    """Owns the current Dataset and notifies the UI when it changes."""

    dataset_changed = pyqtSignal()
    import_failed = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.dataset = Dataset()

    def load_csv(self, path: str) -> None:
        try:
            rows = self._read_csv_rows(path)
        except (OSError, csv.Error) as exc:
            self.import_failed.emit(f"Could not read file: {exc}")
            return

        if not rows:
            self.import_failed.emit("The file has no data rows.")
            return

        header = rows[0]
        body = rows[1:]

        dataset = Dataset()
        numeric_columns: dict[str, list[float]] = {name: [] for name in header[1:]}
        label_column = header[0] if header else "Label"

        for row in body:
            if not row:
                continue
            dataset.labels.append(row[0] if row else "")
            for col_index, col_name in enumerate(header[1:], start=1):
                raw = row[col_index] if col_index < len(row) else ""
                try:
                    numeric_columns[col_name].append(float(raw))
                except ValueError:
                    numeric_columns[col_name].append(float("nan"))

        for name, values in numeric_columns.items():
            dataset.add_series(name, values)

        if not dataset.series:
            self.import_failed.emit(
                "No numeric columns were found after the first column."
            )
            return

        self.dataset = dataset
        self.dataset_changed.emit()

    def load_sample_data(self) -> None:
        dataset = Dataset()
        dataset.labels = [f"T{i}" for i in range(1, 21)]
        dataset.add_series("Measurement A", _sample_series(20, base=10.0, step=0.6))
        dataset.add_series("Measurement B", _sample_series(20, base=6.0, step=0.4, noise=0.8))
        self.dataset = dataset
        self.dataset_changed.emit()

    def set_manual_series(self, name: str, raw_text: str) -> bool:
        """Parse a comma/whitespace separated list of numbers into a series."""
        values = self._parse_numbers(raw_text)
        if not values:
            return False
        existing = self.dataset.get_series(name)
        if existing is not None:
            existing.values = values
        else:
            self.dataset.add_series(name, values)
        if not self.dataset.labels:
            self.dataset.labels = [str(i + 1) for i in range(len(values))]
        self.dataset_changed.emit()
        return True

    def remove_series(self, name: str) -> None:
        self.dataset.remove_series(name)
        self.dataset_changed.emit()

    def summary_stats(self, series_name: str) -> dict[str, float] | None:
        series = self.dataset.get_series(series_name)
        if series is None or not series.values:
            return None
        values = [v for v in series.values if v == v]  # drop NaN
        if not values:
            return None
        result = {
            "count": float(len(values)),
            "mean": statistics.fmean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
        }
        return result

    @staticmethod
    def _read_csv_rows(path: str) -> list[list[str]]:
        with Path(path).open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            return [row for row in reader if row]

    @staticmethod
    def _parse_numbers(raw_text: str) -> list[float]:
        cleaned = raw_text.replace("\n", ",").replace("\t", ",")
        parts = [p.strip() for p in cleaned.split(",")]
        values: list[float] = []
        for part in parts:
            if not part:
                continue
            try:
                values.append(float(part))
            except ValueError:
                continue
        return values


def _sample_series(count: int, base: float, step: float, noise: float = 0.0) -> list[float]:
    import random

    rng = random.Random(42)
    out = []
    current = base
    for _ in range(count):
        current += step + (rng.uniform(-noise, noise) if noise else 0.0)
        out.append(round(current, 2))
    return out
