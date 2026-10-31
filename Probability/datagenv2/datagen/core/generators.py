"""Value generators. Each type turns a parameter string into a callable.

A builder receives the already-split parameter list and a shared
random.Random instance, validates the parameters, and returns a function
that maps a record index to a value. All randomness goes through the shared
Random so a fixed seed reproduces the exact same output.
"""

from __future__ import annotations

import datetime as dt
import uuid as uuid_lib
from dataclasses import dataclass
from random import Random
from typing import Any, Callable

from . import lexicon as lx

Generator = Callable[[int], Any]
Builder = Callable[[list[str], Random], Generator]


@dataclass(frozen=True)
class TypeSpec:
    key: str
    label: str
    hint: str  # placeholder for the parameters box; empty means no parameters
    build: Builder


def split_args(params: str) -> list[str]:
    text = params.strip()
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


# --- parameter helpers -----------------------------------------------------


def _check_count(args: list[str], maximum: int) -> None:
    if len(args) > maximum:
        raise ValueError(f"expected at most {maximum} parameters")


def _arg(args: list[str], index: int, default: str) -> str:
    return args[index] if len(args) > index else default


def _to_int(text: str, label: str) -> int:
    try:
        return int(text)
    except ValueError:
        raise ValueError(f"{label} must be an integer") from None


def _to_float(text: str, label: str) -> float:
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"{label} must be a number") from None


def _to_date(text: str, label: str) -> dt.date:
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        raise ValueError(f"{label} must look like YYYY-MM-DD") from None


def _date_range(args: list[str]) -> tuple[dt.date, dt.date]:
    _check_count(args, 2)
    start = _to_date(_arg(args, 0, "2000-01-01"), "start date")
    end = _to_date(_arg(args, 1, "2025-12-31"), "end date")
    if start > end:
        raise ValueError("start date must not be after end date")
    return start, end


# --- builders --------------------------------------------------------------


def _sequence(args: list[str], rng: Random) -> Generator:
    _check_count(args, 2)
    start = _to_int(_arg(args, 0, "1"), "start")
    step = _to_int(_arg(args, 1, "1"), "step")
    return lambda i: start + i * step


def _uuid(args: list[str], rng: Random) -> Generator:
    _check_count(args, 0)
    return lambda i: str(uuid_lib.UUID(int=rng.getrandbits(128), version=4))


def _integer(args: list[str], rng: Random) -> Generator:
    _check_count(args, 2)
    low = _to_int(_arg(args, 0, "0"), "min")
    high = _to_int(_arg(args, 1, "1000"), "max")
    if low > high:
        raise ValueError("min must not be greater than max")
    return lambda i: rng.randint(low, high)


def _float(args: list[str], rng: Random) -> Generator:
    _check_count(args, 3)
    low = _to_float(_arg(args, 0, "0"), "min")
    high = _to_float(_arg(args, 1, "1"), "max")
    decimals = _to_int(_arg(args, 2, "2"), "decimals")
    if low > high:
        raise ValueError("min must not be greater than max")
    if not 0 <= decimals <= 10:
        raise ValueError("decimals must be between 0 and 10")
    return lambda i: round(rng.uniform(low, high), decimals)


def _boolean(args: list[str], rng: Random) -> Generator:
    _check_count(args, 1)
    chance = _to_float(_arg(args, 0, "0.5"), "probability")
    if not 0.0 <= chance <= 1.0:
        raise ValueError("probability must be between 0 and 1")
    return lambda i: rng.random() < chance


def _date(args: list[str], rng: Random) -> Generator:
    start, end = _date_range(args)
    span = (end - start).days
    return lambda i: (start + dt.timedelta(days=rng.randint(0, span))).isoformat()


def _datetime(args: list[str], rng: Random) -> Generator:
    start, end = _date_range(args)
    base = dt.datetime.combine(start, dt.time.min)
    seconds = int((dt.datetime.combine(end, dt.time.max) - base).total_seconds())
    return lambda i: (
        base + dt.timedelta(seconds=rng.randint(0, seconds))
    ).isoformat(timespec="seconds")


def _choice(args: list[str], rng: Random) -> Generator:
    if not args:
        raise ValueError("give at least one value, separated by commas")
    values = list(args)
    return lambda i: rng.choice(values)


def _pick(words: tuple[str, ...]) -> Builder:
    def build(args: list[str], rng: Random) -> Generator:
        _check_count(args, 0)
        return lambda i: rng.choice(words)

    return build


def _full_name(args: list[str], rng: Random) -> Generator:
    _check_count(args, 0)
    return lambda i: f"{rng.choice(lx.FIRST_NAMES)} {rng.choice(lx.LAST_NAMES)}"


def _email(args: list[str], rng: Random) -> Generator:
    _check_count(args, 0)

    def make(i: int) -> str:
        first = rng.choice(lx.FIRST_NAMES).lower()
        last = rng.choice(lx.LAST_NAMES).lower()
        suffix = str(rng.randint(1, 99)) if rng.random() < 0.4 else ""
        return f"{first}.{last}{suffix}@{rng.choice(lx.EMAIL_DOMAINS)}"

    return make


def _username(args: list[str], rng: Random) -> Generator:
    _check_count(args, 0)

    def make(i: int) -> str:
        first = rng.choice(lx.FIRST_NAMES)[0]
        last = rng.choice(lx.LAST_NAMES)
        return f"{first}{last}{rng.randint(10, 999)}".lower()

    return make


def _phone(args: list[str], rng: Random) -> Generator:
    _check_count(args, 0)
    return lambda i: (
        f"+1-{rng.randint(200, 999)}-{rng.randint(200, 999)}-{rng.randint(0, 9999):04d}"
    )


def _ipv4(args: list[str], rng: Random) -> Generator:
    _check_count(args, 0)
    return lambda i: ".".join(str(rng.randint(1, 254)) for _ in range(4))


def _url(args: list[str], rng: Random) -> Generator:
    _check_count(args, 0)
    return lambda i: (
        f"https://www.{rng.choice(lx.WORDS)}{rng.choice(lx.WORDS)}"
        f".{rng.choice(lx.TLDS)}/{rng.choice(lx.WORDS)}"
    )


def _color(args: list[str], rng: Random) -> Generator:
    _check_count(args, 0)
    return lambda i: f"#{rng.randrange(0x1000000):06x}"


def _sentence(args: list[str], rng: Random) -> Generator:
    _check_count(args, 2)
    low = _to_int(_arg(args, 0, "5"), "min words")
    high = _to_int(_arg(args, 1, "12"), "max words")
    if low < 1:
        raise ValueError("min words must be at least 1")
    if low > high:
        raise ValueError("min words must not be greater than max words")

    def make(i: int) -> str:
        words = [rng.choice(lx.WORDS) for _ in range(rng.randint(low, high))]
        return " ".join(words).capitalize() + "."

    return make


# --- registry --------------------------------------------------------------


def _company(args: list[str], rng: Random) -> Generator:
    _check_count(args, 0)
    return lambda i: (
        f"{rng.choice(lx.COMPANY_PREFIXES)} {rng.choice(lx.COMPANY_SUFFIXES)}"
    )


TYPES: tuple[TypeSpec, ...] = (
    TypeSpec("sequence", "Sequence", "start, step  (default 1, 1)", _sequence),
    TypeSpec("uuid", "UUID", "", _uuid),
    TypeSpec("first_name", "First name", "", _pick(lx.FIRST_NAMES)),
    TypeSpec("last_name", "Last name", "", _pick(lx.LAST_NAMES)),
    TypeSpec("full_name", "Full name", "", _full_name),
    TypeSpec("email", "Email", "", _email),
    TypeSpec("username", "Username", "", _username),
    TypeSpec("phone", "Phone", "", _phone),
    TypeSpec("integer", "Integer", "min, max  (default 0, 1000)", _integer),
    TypeSpec("float", "Float", "min, max, decimals  (default 0, 1, 2)", _float),
    TypeSpec("boolean", "Boolean", "probability of true  (default 0.5)", _boolean),
    TypeSpec("date", "Date", "from, to  (default 2000-01-01, 2025-12-31)", _date),
    TypeSpec(
        "datetime", "Date and time",
        "from, to  (default 2000-01-01, 2025-12-31)", _datetime,
    ),
    TypeSpec("city", "City", "", _pick(lx.CITIES)),
    TypeSpec("country", "Country", "", _pick(lx.COUNTRIES)),
    TypeSpec("company", "Company", "", _company),
    TypeSpec("job_title", "Job title", "", _pick(lx.JOB_TITLES)),
    TypeSpec("word", "Word", "", _pick(lx.WORDS)),
    TypeSpec("sentence", "Sentence", "min words, max words  (default 5, 12)", _sentence),
    TypeSpec("ipv4", "IPv4 address", "", _ipv4),
    TypeSpec("url", "URL", "", _url),
    TypeSpec("color", "Hex color", "", _color),
    TypeSpec("choice", "Choice", "value one, value two, ...", _choice),
)

TYPE_BY_KEY: dict[str, TypeSpec] = {spec.key: spec for spec in TYPES}
