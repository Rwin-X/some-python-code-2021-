"""CSV / Excel loading and column-kind detection. No Qt imports."""

from __future__ import annotations

import os

import pandas as pd

from core.models import ColumnKind, Dataset


SUPPORTED_EXTENSIONS = (".csv", ".tsv", ".txt", ".xlsx", ".xls")


class DataLoadError(Exception):
    """Raised when a file cannot be parsed into a usable table."""


def load_table(path: str) -> pd.DataFrame:
    """Load a CSV/TSV/TXT/XLSX/XLS file into a DataFrame.

    Raises DataLoadError with a human-readable message on failure.
    """
    if not os.path.isfile(path):
        raise DataLoadError(f"File not found: {path}")

    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise DataLoadError(
            f"Unsupported file type '{ext}'. Supported: "
            + ", ".join(SUPPORTED_EXTENSIONS)
        )

    try:
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(path)
        elif ext == ".tsv":
            df = pd.read_csv(path, sep="\t")
        else:
            # Let pandas sniff the delimiter for .csv/.txt as a fallback.
            try:
                df = pd.read_csv(path)
            except Exception:
                df = pd.read_csv(path, sep=None, engine="python")
    except Exception as exc:  # pandas raises many different error types
        raise DataLoadError(f"Could not parse file: {exc}") from exc

    if df.empty or df.shape[1] == 0:
        raise DataLoadError("The file contains no usable columns.")

    # Drop fully-empty unnamed columns pandas sometimes produces from
    # trailing delimiters.
    df = df.loc[:, ~df.columns.astype(str).str.match(r"^Unnamed: \d+$") | df.notna().any()]

    return df


def classify_columns(df: pd.DataFrame) -> dict[str, ColumnKind]:
    """Classify each column as numeric, categorical, or unknown.

    A column is numeric if pandas already infers a numeric dtype, or if
    at least 90% of its non-null values can be coerced to numeric (handles
    numeric columns that were read as strings due to stray characters).
    """
    kinds: dict[str, ColumnKind] = {}
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_numeric_dtype(series):
            kinds[col] = ColumnKind.NUMERIC
            continue

        non_null = series.dropna()
        if len(non_null) == 0:
            kinds[col] = ColumnKind.UNKNOWN
            continue

        coerced = pd.to_numeric(non_null, errors="coerce")
        numeric_fraction = coerced.notna().sum() / len(non_null)
        if numeric_fraction >= 0.9:
            kinds[col] = ColumnKind.NUMERIC
        else:
            kinds[col] = ColumnKind.CATEGORICAL

    return kinds


def coerce_numeric(series: pd.Series) -> pd.Series:
    """Force a series classified as numeric into float dtype, dropping
    unparseable entries (they become NaN and are excluded from stats)."""
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float)
    return pd.to_numeric(series, errors="coerce")


def build_dataset_summary(path: str, df: pd.DataFrame, kinds: dict[str, ColumnKind]) -> Dataset:
    return Dataset(
        source_path=path,
        row_count=len(df),
        column_names=list(df.columns.astype(str)),
        column_kinds=kinds,
    )
