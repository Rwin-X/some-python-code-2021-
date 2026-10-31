"""Plain data classes shared between the engine and the UI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldSpec:
    """One column of the generated records."""

    name: str
    type_key: str
    params: str = ""


@dataclass(frozen=True)
class GenerationConfig:
    """Everything the engine needs to produce one JSON file."""

    fields: tuple[FieldSpec, ...]
    count: int
    path: str
    seed: str | None = None
