"""The release workflow requires both versions to match the tag."""

import json
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_and_pyproject_versions_match():
    manifest = json.loads((ROOT / "custom_components/bru/manifest.json").read_text())
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert manifest["version"] == project["version"]
