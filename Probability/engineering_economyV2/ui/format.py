"""Number formatting helpers shared by all pages."""
import math


def _bad(x) -> bool:
    return x is None or (isinstance(x, float) and not math.isfinite(x))


def fmt(x, digits: int = 2) -> str:
    return "n/a" if _bad(x) else f"{x:,.{digits}f}"


def pct(x, digits: int = 3) -> str:
    return "n/a" if _bad(x) else f"{x * 100:.{digits}f}%"


def pct_list(values, digits: int = 3) -> str:
    return ", ".join(pct(v, digits) for v in values) if values else "none"
