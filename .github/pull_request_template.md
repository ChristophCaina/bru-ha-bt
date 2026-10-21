## What changes

## How it was tested

- [ ] `ruff check` and `ruff format --check`
- [ ] Protocol tests (`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest --ignore=tests/ha`)
- [ ] Home Assistant tests (`pytest -o asyncio_mode=auto tests/ha`)
- [ ] On a real machine (which firmware?)

## Version

- [ ] `manifest.json` and `pyproject.toml` versions bumped together, if this is a release
