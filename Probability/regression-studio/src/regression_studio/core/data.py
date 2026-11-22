"""Parsing and validation of user-entered tabular data. No Qt imports."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import numpy as np

from .models import AnalysisError

# Persian and Arabic-Indic digits are accepted alongside ASCII digits.
_PERSIAN = "".join(chr(0x06F0 + i) for i in range(10))
_ARABIC = "".join(chr(0x0660 + i) for i in range(10))
_TRANSLATION = str.maketrans(
    _PERSIAN + _ARABIC + chr(0x066B), "0123456789" * 2 + ".", chr(0x066C)
)
_MISSING = {"", "na", "n/a", "nan", "null", "none", "-"}


class DataError(AnalysisError):
    """The table contents cannot be used for the requested analysis."""


def parse_cell(text: str) -> float | None:
    """Return a float, None for a missing value, or raise ValueError."""
    s = text.strip().translate(_TRANSLATION)
    if s.lower() in _MISSING:
        return None
    if "," in s and "." not in s:
        s = s.replace(",", ".")  # decimal comma
    value = float(s)
    return value if math.isfinite(value) else None


@dataclass
class Selection:
    x: np.ndarray  # (n, k)
    y: np.ndarray  # (n,)
    n_dropped: int  # rows with some, but not all, selected values missing
    rows: np.ndarray  # 0-based table row index of every kept row


class Dataset:
    """Numeric view of a text table, column by column."""

    def __init__(
        self,
        columns: dict[str, np.ndarray],
        problems: dict[str, tuple[int, str]],
    ) -> None:
        self.columns = columns
        self.problems = problems  # name -> (row number, offending text)

    def _require(self, name: str) -> np.ndarray:
        if name in self.columns:
            return self.columns[name]
        if name in self.problems:
            row, text = self.problems[name]
            raise DataError(
                f"Column '{name}' is not numeric: found '{text}' in row {row}."
            )
        raise DataError(f"Column '{name}' does not exist.")

    def extract(self, x_cols: tuple[str, ...], y_col: str) -> Selection:
        if not x_cols:
            raise DataError("Select at least one predictor column.")
        if y_col in x_cols:
            raise DataError("The response column cannot also be a predictor.")
        x = np.column_stack([self._require(c) for c in x_cols])
        y = self._require(y_col)
        present_x = np.isfinite(x)
        present_y = np.isfinite(y)
        keep = present_x.all(axis=1) & present_y
        if not keep.any():
            raise DataError("No complete rows: fill in the selected columns.")
        started = present_x.any(axis=1) | present_y
        return Selection(x[keep], y[keep], int((started & ~keep).sum()), np.flatnonzero(keep))


def build_dataset(headers: list[str], rows: list[list[str]]) -> Dataset:
    if any(not h.strip() for h in headers):
        raise DataError("Column names must not be empty.")
    if len(set(headers)) != len(headers):
        raise DataError("Column names must be unique.")
    n = len(rows)
    columns: dict[str, np.ndarray] = {}
    problems: dict[str, tuple[int, str]] = {}
    for j, name in enumerate(headers):
        values = np.full(n, np.nan)
        bad: tuple[int, str] | None = None
        for i, row in enumerate(rows):
            cell = row[j] if j < len(row) else ""
            try:
                parsed = parse_cell(cell)
            except ValueError:
                bad = (i + 1, cell.strip())
                break
            if parsed is not None:
                values[i] = parsed
        if bad is not None:
            problems[name] = bad
        else:
            columns[name] = values
    return Dataset(columns, problems)


def parse_points(text: str, n_predictors: int) -> np.ndarray:
    """Parse prediction input into an (m, k) array.

    One predictor: any mix of commas, semicolons and spaces separates points.
    Several predictors: values within a point are separated by commas or
    spaces, points by semicolons or new lines.
    """
    text = text.strip().translate(_TRANSLATION)
    if not text:
        raise DataError("Enter at least one value to predict.")
    points: list[list[float]] = []
    try:
        if n_predictors == 1:
            points = [[float(t)] for t in re.split(r"[,;\s]+", text) if t]
        else:
            for chunk in text.replace("\n", ";").split(";"):
                tokens = [t for t in re.split(r"[,\s]+", chunk.strip()) if t]
                if not tokens:
                    continue
                if len(tokens) != n_predictors:
                    raise DataError(
                        f"Each point needs {n_predictors} values (one per predictor)."
                    )
                points.append([float(t) for t in tokens])
    except ValueError:
        raise DataError("Could not read the values; use plain numbers.") from None
    if not points:
        raise DataError("Enter at least one value to predict.")
    arr = np.array(points, dtype=float)
    if not np.isfinite(arr).all():
        raise DataError("Values must be finite numbers.")
    return arr


def sample_table() -> tuple[list[str], list[list[str]]]:
    """Demo data: a noisy quadratic in x, with a second predictor z."""
    rng = np.random.default_rng(42)
    x = np.linspace(0.5, 10.0, 40)
    z = rng.uniform(0.0, 5.0, x.size)
    y = 1.5 + 2.0 * x - 0.15 * x**2 + 1.2 * z + rng.normal(0.0, 0.8, x.size)
    rows = [[f"{a:.4f}", f"{b:.4f}", f"{c:.4f}"] for a, b, c in zip(x, z, y)]
    return ["x", "z", "y"], rows
