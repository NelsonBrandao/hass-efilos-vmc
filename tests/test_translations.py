"""Every translation must cover exactly the keys in strings.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

INTEGRATION = Path(__file__).parent.parent / "custom_components" / "efilos_vmc"


def _keys(obj: dict, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for key, value in obj.items():
        path = f"{prefix}.{key}" if prefix else key
        keys |= _keys(value, path) if isinstance(value, dict) else {path}
    return keys


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_english_matches_strings() -> None:
    assert _load(INTEGRATION / "translations" / "en.json") == _load(INTEGRATION / "strings.json")


@pytest.mark.parametrize(
    "translation", sorted((INTEGRATION / "translations").glob("*.json")), ids=lambda p: p.stem
)
def test_translation_keys_match(translation: Path) -> None:
    assert _keys(_load(translation)) == _keys(_load(INTEGRATION / "strings.json"))
