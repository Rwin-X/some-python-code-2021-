"""Validation and file writing. No Qt imports."""

from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Callable

from .formats import FORMAT_BY_KEY
from .generators import TYPE_BY_KEY, split_args
from .models import FieldSpec, GenerationConfig

MAX_RECORDS = 5_000_000


class Cancelled(Exception):
    """Raised inside write_output when the caller asks to stop."""


def resolve_path(raw: str, extension: str = ".json") -> Path:
    text = raw.strip()
    if not text:
        raise ValueError("Choose an output file")
    path = Path(text).expanduser()
    if path.is_dir():
        raise ValueError("Output path is a folder, not a file")
    if path.suffix == "":
        path = path.with_suffix(extension)
    return path


def build_row_factory(
    fields: tuple[FieldSpec, ...], rng: random.Random
) -> Callable[[int], dict]:
    columns = []
    for spec in fields:
        type_spec = TYPE_BY_KEY.get(spec.type_key)
        if type_spec is None:
            raise ValueError(f"Field '{spec.name}': unknown type")
        try:
            generator = type_spec.build(split_args(spec.params), rng)
        except ValueError as exc:
            raise ValueError(f"Field '{spec.name}': {exc}") from None
        columns.append((spec.name, generator))

    def make_row(index: int) -> dict:
        return {name: generator(index) for name, generator in columns}

    return make_row


def validate(config: GenerationConfig) -> Path:
    """Check the whole configuration and return the resolved output path."""
    if not config.fields:
        raise ValueError("Add at least one field")

    seen: set[str] = set()
    for spec in config.fields:
        name = spec.name.strip()
        if not name:
            raise ValueError("Every field needs a name")
        if name in seen:
            raise ValueError(f"Duplicate field name: {name}")
        seen.add(name)

    if not 1 <= config.count <= MAX_RECORDS:
        raise ValueError(f"Records must be between 1 and {MAX_RECORDS:,}")

    format_spec = FORMAT_BY_KEY.get(config.format_key)
    if format_spec is None:
        raise ValueError("Unknown output format")

    path = resolve_path(config.path, format_spec.extension)
    if not path.parent.exists():
        raise ValueError("Output folder does not exist")

    build_row_factory(config.fields, random.Random(0))
    return path


def write_output(
    config: GenerationConfig,
    on_progress: Callable[[int], None],
    is_cancelled: Callable[[], bool],
) -> Path:
    """Stream records into the chosen format. Returns the final path.

    The data is written to '<name>.part' first and renamed on success, so a
    cancelled or failed run never leaves a half-written output file behind.
    """
    format_spec = FORMAT_BY_KEY[config.format_key]
    target = resolve_path(config.path, format_spec.extension)
    rng = random.Random() if config.seed is None else random.Random(config.seed)
    make_row = build_row_factory(config.fields, rng)
    writer = format_spec.create([spec.name for spec in config.fields], target.stem)

    total = config.count
    step = max(1, min(total // 200, 2000))
    last_percent = -1
    partial = target.with_name(target.name + ".part")

    try:
        with open(partial, "w", encoding="utf-8", newline="") as handle:
            writer.start(handle)
            for index in range(total):
                if index % step == 0:
                    if is_cancelled():
                        raise Cancelled()
                    percent = index * 100 // total
                    if percent != last_percent:
                        last_percent = percent
                        on_progress(percent)
                writer.row(handle, make_row(index), index == total - 1)
            writer.finish(handle)
        os.replace(partial, target)
    except BaseException:
        try:
            partial.unlink()
        except OSError:
            pass
        raise

    on_progress(100)
    return target
