"""Load a JSON dataset (see data/hydraulic_jack_dataset.json)."""
import json


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("Dataset must be a JSON object")
    return data
