"""Pure statistics helpers used for chart overlays. No PyQt imports at all."""

from __future__ import annotations

import math


def linear_fit(x_values: list[float], y_values: list[float]) -> tuple[float, float] | None:
    """Least-squares fit y = slope * x + intercept. Returns None if undefined."""
    pairs = [(x, y) for x, y in zip(x_values, y_values) if y == y]  # drop NaN
    n = len(pairs)
    if n < 2:
        return None

    mean_x = sum(p[0] for p in pairs) / n
    mean_y = sum(p[1] for p in pairs) / n

    denominator = sum((p[0] - mean_x) ** 2 for p in pairs)
    if denominator == 0:
        return None

    numerator = sum((p[0] - mean_x) * (p[1] - mean_y) for p in pairs)
    slope = numerator / denominator
    intercept = mean_y - slope * mean_x
    return slope, intercept


def moving_average(values: list[float], window: int) -> list[float]:
    """Centered simple moving average. NaN where the window doesn't fit."""
    if window < 1:
        return list(values)

    result: list[float] = []
    half = window // 2
    for i in range(len(values)):
        start = max(0, i - half)
        end = min(len(values), i + half + (window % 2))
        chunk = [v for v in values[start:end] if v == v]
        result.append(sum(chunk) / len(chunk) if chunk else float("nan"))
    return result


def normalize_min_max(values: list[float]) -> list[float]:
    """Scale values to [0, 1]. Returns zeros if the range is degenerate."""
    clean = [v for v in values if v == v]
    if not clean:
        return list(values)
    lo, hi = min(clean), max(clean)
    if hi == lo:
        return [0.0 for _ in values]
    return [((v - lo) / (hi - lo)) if v == v else float("nan") for v in values]


def standard_error(values: list[float]) -> float:
    """Standard error of the mean. 0.0 for fewer than 2 valid points."""
    clean = [v for v in values if v == v]
    if len(clean) < 2:
        return 0.0
    mean = sum(clean) / len(clean)
    variance = sum((v - mean) ** 2 for v in clean) / (len(clean) - 1)
    return math.sqrt(variance / len(clean))
