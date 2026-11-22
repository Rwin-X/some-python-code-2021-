"""Reading and writing delimited text. No Qt imports."""

from __future__ import annotations

import csv
from pathlib import Path

from .data import parse_cell
from .models import AnalysisError


def parse_delimited(text: str) -> list[list[str]]:
    """Split pasted or file text into a rectangular list of cells.

    The delimiter is taken from the first line: tab, semicolon, comma, or
    whitespace as the fallback.
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    first = lines[0]
    if "\t" in first:
        delimiter = "\t"
    elif ";" in first:
        delimiter = ";"
    elif "," in first:
        delimiter = ","
    else:
        delimiter = None
    if delimiter:
        rows = list(csv.reader(lines, delimiter=delimiter))
    else:
        rows = [ln.split() for ln in lines]
    width = max(len(r) for r in rows)
    return [[c.strip() for c in r] + [""] * (width - len(r)) for r in rows]


def looks_like_header(row: list[str]) -> bool:
    """A row is a header when at least one cell is not a number."""
    for cell in row:
        try:
            parse_cell(cell)
        except ValueError:
            return True
    return False


def clean_headers(headers: list[str]) -> list[str]:
    """Replace blank names and make duplicates unique."""
    seen: set[str] = set()
    result: list[str] = []
    for i, raw in enumerate(headers):
        name = raw.strip() or f"col{i + 1}"
        candidate, suffix = name, 2
        while candidate in seen:
            candidate = f"{name}_{suffix}"
            suffix += 1
        seen.add(candidate)
        result.append(candidate)
    return result


def read_table(path: str) -> tuple[list[str], list[list[str]]]:
    text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    rows = parse_delimited(text)
    if not rows:
        raise AnalysisError("The file is empty.")
    if looks_like_header(rows[0]):
        return clean_headers(rows[0]), rows[1:]
    return clean_headers([""] * len(rows[0])), rows


def write_csv(path: str, headers: list[str], rows: list[list[str]]) -> int:
    """Write the table, skipping fully blank rows. Returns rows written."""
    written = 0
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        for row in rows:
            if any(cell.strip() for cell in row):
                writer.writerow(row)
                written += 1
    return written
