"""The files HACS copies or requires when installing the integration."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "bru"


def test_hacs_manifest_and_bundled_library():
    assert (ROOT / "hacs.json").is_file()
    assert (ROOT / "brand" / "icon.png").is_file()
    assert (COMPONENT / "bru_ble" / "__init__.py").is_file()
    assert not (ROOT / "bru_ble").exists()

    hacs = json.loads((ROOT / "hacs.json").read_text())
    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    assert hacs["name"] == "BRU Maker One"
    assert manifest["domain"] == "bru"
    assert manifest["version"]
    assert manifest["documentation"].startswith("https://")
    assert manifest["issue_tracker"].startswith("https://")
    assert manifest["codeowners"] == ["@saschaludwig"]
    assert list(COMPONENT.glob("library.py")) == []
