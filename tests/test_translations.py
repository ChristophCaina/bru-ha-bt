"""Custom integrations read translations/<lang>.json, not strings.json."""

import json
from pathlib import Path

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "bru"


def _keys(data, prefix=""):
    if isinstance(data, dict):
        out = set()
        for key, value in data.items():
            out |= _keys(value, f"{prefix}{key}.")
        return out
    return {prefix.rstrip(".")}


def test_english_matches_strings():
    strings = json.loads((COMPONENT / "strings.json").read_text())
    english = json.loads((COMPONENT / "translations" / "en.json").read_text())
    assert english == strings


def test_german_has_every_key():
    strings = json.loads((COMPONENT / "strings.json").read_text())
    german = json.loads((COMPONENT / "translations" / "de.json").read_text())
    assert _keys(german) == _keys(strings)


def test_every_icon_belongs_to_a_translated_entity():
    strings = json.loads((COMPONENT / "strings.json").read_text())
    icons = json.loads((COMPONENT / "icons.json").read_text())
    for platform, entities in icons["entity"].items():
        for key in entities:
            assert key in strings["entity"][platform], f"{platform}.{key}"
    assert set(icons["services"]) == set(strings["services"])


def test_every_status_key_is_translated():
    from bru_ble.status import STATE_KEYS

    for name in ("strings.json", "translations/de.json"):
        data = json.loads((COMPONENT / name).read_text())
        states = data["entity"]["sensor"]["status"]["state"]
        assert set(states) == set(STATE_KEYS), name


def test_every_known_code_maps_to_a_key():
    from bru_ble.status import (
        STATE_KEYS,
        STATUS_NAMES,
        SUBSTATUS_NAMES,
        MachineState,
    )

    for status in [*STATUS_NAMES, 250]:
        for sub in [*SUBSTATUS_NAMES, 250]:
            key = MachineState(status_code=status, sub_status_code=sub).key
            assert key in STATE_KEYS
    assert MachineState().key is None
    assert MachineState(status_code=5, sub_status_code=26).key == "steeping"
    assert MachineState(status_code=1, sub_status_code=2).key == "idle"
    assert MachineState(status_code=22, sub_status_code=95).key == "descaling"
    assert MachineState(status_code=99, sub_status_code=0).key == "other"
