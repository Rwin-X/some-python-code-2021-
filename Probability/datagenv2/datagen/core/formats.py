"""Output formats. Every writer streams one record at a time."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from typing import Any, Callable, TextIO
from xml.sax.saxutils import escape


class Writer:
    """Base class: start() -> row() for every record -> finish()."""

    def __init__(self, columns: list[str], table: str):
        self.columns = columns
        self.table = table

    def start(self, handle: TextIO) -> None:
        pass

    def row(self, handle: TextIO, record: dict, last: bool) -> None:
        raise NotImplementedError

    def finish(self, handle: TextIO) -> None:
        pass


class JsonWriter(Writer):
    def start(self, handle: TextIO) -> None:
        handle.write("[\n")

    def row(self, handle: TextIO, record: dict, last: bool) -> None:
        body = json.dumps(record, indent=2, ensure_ascii=False)
        handle.write("\n".join("  " + line for line in body.splitlines()))
        handle.write("\n" if last else ",\n")

    def finish(self, handle: TextIO) -> None:
        handle.write("]\n")


class JsonLinesWriter(Writer):
    def row(self, handle: TextIO, record: dict, last: bool) -> None:
        handle.write(json.dumps(record, ensure_ascii=False))
        handle.write("\n")


def _plain(value: Any) -> Any:
    return str(value).lower() if isinstance(value, bool) else value


class DelimitedWriter(Writer):
    delimiter = ","

    def start(self, handle: TextIO) -> None:
        self._csv = csv.writer(handle, delimiter=self.delimiter, lineterminator="\n")
        self._csv.writerow(self.columns)

    def row(self, handle: TextIO, record: dict, last: bool) -> None:
        self._csv.writerow([_plain(record[name]) for name in self.columns])


class CsvWriter(DelimitedWriter):
    delimiter = ","


class TsvWriter(DelimitedWriter):
    delimiter = "\t"


def _sql_literal(value: Any) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return repr(value)
    return "'" + str(value).replace("'", "''") + "'"


def _sql_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _sql_table_name(raw: str) -> str:
    cleaned = re.sub(r"\W", "_", raw) or "data"
    return cleaned if not cleaned[0].isdigit() else "t_" + cleaned


class SqlWriter(Writer):
    """One INSERT statement per record. The table name is the file name."""

    def __init__(self, columns: list[str], table: str):
        super().__init__(columns, _sql_table_name(table))
        self._prefix = (
            f"INSERT INTO {_sql_identifier(self.table)} ("
            + ", ".join(_sql_identifier(name) for name in columns)
            + ") VALUES ("
        )

    def row(self, handle: TextIO, record: dict, last: bool) -> None:
        values = ", ".join(_sql_literal(record[name]) for name in self.columns)
        handle.write(self._prefix + values + ");\n")


def _xml_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    return cleaned if re.match(r"[A-Za-z_]", cleaned) else "_" + cleaned


class XmlWriter(Writer):
    def __init__(self, columns: list[str], table: str):
        super().__init__(columns, table)
        self._tags = {name: _xml_name(name) for name in columns}

    def start(self, handle: TextIO) -> None:
        handle.write('<?xml version="1.0" encoding="UTF-8"?>\n<records>\n')

    def row(self, handle: TextIO, record: dict, last: bool) -> None:
        handle.write("  <record>\n")
        for name in self.columns:
            tag = self._tags[name]
            text = escape(str(_plain(record[name])))
            handle.write(f"    <{tag}>{text}</{tag}>\n")
        handle.write("  </record>\n")

    def finish(self, handle: TextIO) -> None:
        handle.write("</records>\n")


@dataclass(frozen=True)
class FormatSpec:
    key: str
    label: str
    extension: str
    create: Callable[[list[str], str], Writer]


FORMATS: tuple[FormatSpec, ...] = (
    FormatSpec("json", "JSON", ".json", JsonWriter),
    FormatSpec("jsonl", "JSON Lines", ".jsonl", JsonLinesWriter),
    FormatSpec("csv", "CSV", ".csv", CsvWriter),
    FormatSpec("tsv", "TSV", ".tsv", TsvWriter),
    FormatSpec("sql", "SQL inserts", ".sql", SqlWriter),
    FormatSpec("xml", "XML", ".xml", XmlWriter),
)

FORMAT_BY_KEY: dict[str, FormatSpec] = {spec.key: spec for spec in FORMATS}
KNOWN_EXTENSIONS: frozenset[str] = frozenset(spec.extension for spec in FORMATS)
