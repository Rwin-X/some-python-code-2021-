# Data Generator

Minimal desktop tool that generates random records and writes them to a JSON file.

## Features

- Define fields by name and type; 23 built-in types (sequence, UUID, names, email,
  username, phone, integer, float, boolean, date, date and time, city, country,
  company, job title, word, sentence, IPv4, URL, hex color, choice)
- Per-field parameters, such as `18, 90` for an integer range or `red, green, blue` for a choice
- Choose how many records to generate (up to 5,000,000)
- Optional seed: the same seed reproduces identical data, an empty seed gives new data every run
- Generation runs on a background thread with a progress bar and a Cancel button
- Output is written to a temporary `.part` file and renamed on success, so a cancelled
  run never leaves a broken `.json` file behind
- No dependencies besides PyQt6; all word lists are built in

## Requirements

- Python 3.10 or newer
- PyQt6

## Installation and run

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py        # or: python -m datagen
```

## Parameters

| Type | Parameters | Default |
|------|------------|---------|
| Sequence | `start, step` | `1, 1` |
| Integer | `min, max` | `0, 1000` |
| Float | `min, max, decimals` | `0, 1, 2` |
| Boolean | probability of true, 0 to 1 | `0.5` |
| Date / Date and time | `from, to` as `YYYY-MM-DD` | `2000-01-01, 2025-12-31` |
| Sentence | `min words, max words` | `5, 12` |
| Choice | values separated by commas | required |

All other types take no parameters.

## Tests

```bash
pip install pytest
QT_QPA_PLATFORM=offscreen python -m pytest tests
```

## Project structure

```
datagen/
├── main.py             # builds QApplication and shows the window
├── core/               # no widgets; usable and testable without a display
│   ├── models.py        # FieldSpec, GenerationConfig
│   ├── lexicon.py       # built-in word lists
│   ├── generators.py    # type registry and value generators
│   ├── engine.py        # validation and streaming JSON writer
│   └── worker.py        # QObject worker for the background thread
└── ui/
    ├── style.py         # palette and stylesheet
    ├── widgets.py       # title bar, glyph buttons, field row
    └── main_window.py   # main window
```
