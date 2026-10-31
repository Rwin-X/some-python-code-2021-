import csv
import json
import random
import sqlite3
import xml.etree.ElementTree as ET

import pytest

from datagen.core import engine
from datagen.core.generators import TYPES, TYPE_BY_KEY, split_args
from datagen.core.models import FieldSpec, GenerationConfig


def make_config(tmp_path, fields, count=50, seed="abc", name="out.json"):
    return GenerationConfig(
        fields=tuple(fields), count=count, path=str(tmp_path / name), seed=seed
    )


def test_every_type_builds_with_defaults():
    rng = random.Random(1)
    for spec in TYPES:
        args = ["a", "b"] if spec.key == "choice" else []
        json.dumps(spec.build(args, rng)(0))


def test_write_json_structure(tmp_path):
    config = make_config(
        tmp_path,
        [FieldSpec("id", "sequence", "10, 5"), FieldSpec("age", "integer", "18, 20")],
        count=25,
    )
    path = engine.write_output(config, lambda p: None, lambda: False)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data) == 25
    assert data[0] == {"id": 10, "age": data[0]["age"]}
    assert data[3]["id"] == 25
    assert all(18 <= row["age"] <= 20 for row in data)
    assert not list(tmp_path.glob("*.part"))


def test_same_seed_is_reproducible(tmp_path):
    fields = [
        FieldSpec(t.key, t.key, "a, b" if t.key == "choice" else "") for t in TYPES
    ]
    a = engine.write_output(make_config(tmp_path, fields, seed="s1", name="a.json"),
                          lambda p: None, lambda: False)
    b = engine.write_output(make_config(tmp_path, fields, seed="s1", name="b.json"),
                          lambda p: None, lambda: False)
    c = engine.write_output(make_config(tmp_path, fields, seed="s2", name="c.json"),
                          lambda p: None, lambda: False)
    assert a.read_text() == b.read_text()
    assert a.read_text() != c.read_text()


def test_no_seed_differs_between_runs(tmp_path):
    fields = [FieldSpec("n", "integer", "0, 1000000000")]
    a = engine.write_output(make_config(tmp_path, fields, seed=None, name="a.json"),
                          lambda p: None, lambda: False)
    b = engine.write_output(make_config(tmp_path, fields, seed=None, name="b.json"),
                          lambda p: None, lambda: False)
    assert a.read_text() != b.read_text()


def test_cancel_leaves_no_files(tmp_path):
    config = make_config(tmp_path, [FieldSpec("w", "word")], count=100_000)
    calls = {"n": 0}

    def cancelled():
        calls["n"] += 1
        return calls["n"] > 3

    with pytest.raises(engine.Cancelled):
        engine.write_output(config, lambda p: None, cancelled)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "fields, count, message",
    [
        ([], 5, "at least one field"),
        ([FieldSpec("", "word")], 5, "needs a name"),
        ([FieldSpec("a", "word"), FieldSpec("a", "city")], 5, "Duplicate"),
        ([FieldSpec("a", "integer", "9, 1")], 5, "min must not be greater"),
        ([FieldSpec("a", "integer", "x, 1")], 5, "must be an integer"),
        ([FieldSpec("a", "date", "2025-01-01, 2020-01-01")], 5, "after end"),
        ([FieldSpec("a", "date", "yesterday")], 5, "YYYY-MM-DD"),
        ([FieldSpec("a", "boolean", "2")], 5, "between 0 and 1"),
        ([FieldSpec("a", "choice", "")], 5, "at least one value"),
        ([FieldSpec("a", "uuid", "1")], 5, "at most 0"),
        ([FieldSpec("a", "word")], 0, "Records must be"),
    ],
)
def test_validation_errors(tmp_path, fields, count, message):
    config = make_config(tmp_path, fields, count=count)
    with pytest.raises(ValueError, match=message):
        engine.validate(config)


def test_path_rules(tmp_path):
    fields = [FieldSpec("a", "word")]
    assert engine.validate(make_config(tmp_path, fields, name="noext")).suffix == ".json"
    with pytest.raises(ValueError, match="folder does not exist"):
        engine.validate(make_config(tmp_path, fields, name="missing/x.json"))
    with pytest.raises(ValueError, match="folder, not a file"):
        engine.validate(GenerationConfig(tuple(fields), 1, str(tmp_path), None))


def test_choice_and_split_args():
    assert split_args(" a, b ,, c ") == ["a", "b", "c"]
    gen = TYPE_BY_KEY["choice"].build(["x", "y"], random.Random(3))
    assert {gen(i) for i in range(50)} == {"x", "y"}


def make_format_config(tmp_path, fmt, fields, count=40):
    return GenerationConfig(
        fields=tuple(fields), count=count, path=str(tmp_path / "out"),
        seed="fmt", format_key=fmt,
    )


FORMAT_FIELDS = [
    FieldSpec("id", "sequence"),
    FieldSpec("first name", "first_name"),
    FieldSpec("flag", "boolean"),
    FieldSpec("score", "float", "0, 10, 3"),
    FieldSpec("note", "choice", "it's, a \"quote\", x"),
]


def run(tmp_path, fmt, count=40):
    config = make_format_config(tmp_path, fmt, FORMAT_FIELDS, count)
    return engine.write_output(config, lambda p: None, lambda: False)


def test_extensions_follow_format(tmp_path):
    for key, ext in [("json", ".json"), ("jsonl", ".jsonl"), ("csv", ".csv"),
                     ("tsv", ".tsv"), ("sql", ".sql"), ("xml", ".xml")]:
        assert run(tmp_path, key, 3).suffix == ext


def test_jsonl_format(tmp_path):
    lines = run(tmp_path, "jsonl").read_text().splitlines()
    assert len(lines) == 40
    assert json.loads(lines[0])["id"] == 1


def test_csv_and_tsv_format(tmp_path):
    for key, delimiter in (("csv", ","), ("tsv", "\t")):
        path = run(tmp_path, key)
        with open(path, newline="", encoding="utf-8") as handle:
            rows = list(csv.reader(handle, delimiter=delimiter))
        assert rows[0] == ["id", "first name", "flag", "score", "note"]
        assert len(rows) == 41
        assert rows[1][2] in ("true", "false")


def test_sql_format_loads_into_sqlite(tmp_path):
    path = run(tmp_path, "sql")
    db = sqlite3.connect(":memory:")
    db.execute(
        'CREATE TABLE "out" ("id" INT, "first name" TEXT, "flag" INT, "score" REAL, "note" TEXT)'
    )
    db.executescript(path.read_text(encoding="utf-8"))
    assert db.execute('SELECT COUNT(*) FROM "out"').fetchone()[0] == 40
    notes = {row[0] for row in db.execute('SELECT "note" FROM "out"')}
    assert notes <= {"it's", 'a "quote"', "x"}


def test_xml_format_is_well_formed(tmp_path):
    root = ET.parse(run(tmp_path, "xml")).getroot()
    records = root.findall("record")
    assert len(records) == 40
    assert records[0].find("first_name") is not None
    assert records[0].find("id").text == "1"


def test_unknown_format_rejected(tmp_path):
    config = make_format_config(tmp_path, "yaml", FORMAT_FIELDS)
    with pytest.raises(ValueError, match="Unknown output format"):
        engine.validate(config)
