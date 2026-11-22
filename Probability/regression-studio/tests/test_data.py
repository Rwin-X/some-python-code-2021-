import numpy as np
import pytest

from regression_studio.core.data import DataError, build_dataset, parse_cell, parse_points
from regression_studio.core.io import clean_headers, looks_like_header, parse_delimited, read_table, write_csv


def test_parse_cell_variants():
    assert parse_cell(" 3.5 ") == 3.5
    assert parse_cell("2,5") == 2.5
    assert parse_cell("") is None
    assert parse_cell("NA") is None
    assert parse_cell("\u06f1\u06f2.\u06f5") == 12.5  # Persian digits
    assert parse_cell("\u0661\u0662\u066b\u0665") == 12.5  # Arabic-Indic digits
    with pytest.raises(ValueError):
        parse_cell("abc")


def test_extract_drops_incomplete_rows_but_ignores_blank_ones():
    headers = ["x", "y"]
    rows = [["1", "2"], ["2", ""], ["", ""], ["3", "6"], ["4", "8"]]
    sel = build_dataset(headers, rows).extract(("x",), "y")
    assert sel.x[:, 0].tolist() == [1.0, 3.0, 4.0]
    assert sel.n_dropped == 1  # only the half-filled row counts


def test_non_numeric_column_reports_location():
    ds = build_dataset(["x", "label"], [["1", "a"], ["2", "b"]])
    with pytest.raises(DataError, match="row 1"):
        ds.extract(("x",), "label")


def test_selection_validation():
    ds = build_dataset(["x", "y"], [["1", "2"], ["2", "3"]])
    with pytest.raises(DataError):
        ds.extract((), "y")
    with pytest.raises(DataError):
        ds.extract(("y",), "y")
    with pytest.raises(DataError):
        ds.extract(("missing",), "y")
    with pytest.raises(DataError):
        build_dataset(["x", "x"], [["1", "2"]])


def test_parse_points():
    assert parse_points("1, 2; 3 4", 1).ravel().tolist() == [1, 2, 3, 4]
    assert parse_points("1, 2; 3, 4", 2).tolist() == [[1, 2], [3, 4]]
    with pytest.raises(DataError):
        parse_points("1, 2, 3", 2)
    with pytest.raises(DataError):
        parse_points("", 1)
    with pytest.raises(DataError):
        parse_points("abc", 1)


def test_parse_delimited_detects_delimiters():
    assert parse_delimited("a\tb\n1\t2") == [["a", "b"], ["1", "2"]]
    assert parse_delimited("a;b\n1;2") == [["a", "b"], ["1", "2"]]
    assert parse_delimited("a,b\n1,2\n\n") == [["a", "b"], ["1", "2"]]
    assert parse_delimited("1 2\n3 4") == [["1", "2"], ["3", "4"]]
    assert parse_delimited("1,2\n3") == [["1", "2"], ["3", ""]]


def test_headers():
    assert looks_like_header(["x", "y"])
    assert not looks_like_header(["1", "2.5"])
    assert clean_headers(["a", "a", ""]) == ["a", "a_2", "col3"]


def test_csv_roundtrip(tmp_path):
    path = tmp_path / "d.csv"
    assert write_csv(str(path), ["x", "y"], [["1", "2"], ["", ""], ["3", "4"]]) == 2
    headers, rows = read_table(str(path))
    assert headers == ["x", "y"]
    assert rows == [["1", "2"], ["3", "4"]]


def test_headerless_csv_gets_generated_names(tmp_path):
    path = tmp_path / "d.csv"
    path.write_text("1,2\n3,4\n", encoding="utf-8")
    headers, rows = read_table(str(path))
    assert headers == ["col1", "col2"]
    assert len(rows) == 2
