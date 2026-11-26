"""Tests for core/stats.py. Pure functions, no PyQt required to run these."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.stats import linear_fit, moving_average, normalize_min_max, standard_error


def test_linear_fit_exact_line():
    x = [0, 1, 2, 3, 4]
    y = [1, 3, 5, 7, 9]  # y = 2x + 1
    slope, intercept = linear_fit(x, y)
    assert math.isclose(slope, 2.0, abs_tol=1e-9)
    assert math.isclose(intercept, 1.0, abs_tol=1e-9)


def test_linear_fit_ignores_nan():
    x = [0, 1, 2, 3, 4]
    y = [1, 3, float("nan"), 7, 9]
    result = linear_fit(x, y)
    assert result is not None
    slope, intercept = result
    assert math.isclose(slope, 2.0, abs_tol=1e-9)


def test_linear_fit_degenerate_returns_none():
    assert linear_fit([1, 1, 1], [2, 3, 4]) is None
    assert linear_fit([1], [2]) is None


def test_moving_average_basic():
    result = moving_average([1, 2, 3, 4, 5], window=3)
    assert result == [1.5, 2.0, 3.0, 4.0, 4.5]


def test_moving_average_window_one_is_identity():
    values = [1, 2, 3]
    assert moving_average(values, window=1) == [1.0, 2.0, 3.0]


def test_normalize_min_max_basic():
    assert normalize_min_max([0, 5, 10]) == [0.0, 0.5, 1.0]


def test_normalize_min_max_degenerate():
    assert normalize_min_max([5, 5, 5]) == [0.0, 0.0, 0.0]


def test_standard_error_increases_with_spread():
    tight = standard_error([5.0, 5.1, 4.9, 5.0])
    spread = standard_error([1.0, 9.0, 2.0, 8.0])
    assert spread > tight


def test_standard_error_needs_two_points():
    assert standard_error([5.0]) == 0.0
    assert standard_error([]) == 0.0


if __name__ == "__main__":
    tests = [obj for name, obj in list(globals().items()) if name.startswith("test_")]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS  {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL  {test.__name__}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
