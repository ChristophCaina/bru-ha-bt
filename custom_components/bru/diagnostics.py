"""Diagnostics download with recent raw advertisements."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import BruConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: BruConfigEntry
) -> dict[str, Any]:
    """Return state, brew settings, and the raw advertisement log."""
    coordinator = entry.runtime_data
    state = coordinator.state
    return {
        "available": coordinator.available,
        "state": {
            "status": state.status,
            "sub_status": state.sub_status,
            "status_code": state.status_code,
            "sub_status_code": state.sub_status_code,
            "source": state.source,
            "busy": state.busy,
            "brewing": coordinator.brewing,
        },
        "timing": {
            "steeping_since": coordinator.steeping_since,
            "ready_at": coordinator.ready_at,
        },
        "settings": {
            "temperature_c": coordinator.temperature_c,
            "steep_seconds": coordinator.steep_seconds,
            "water_ml": coordinator.water_ml,
        },
        "rssi": coordinator.rssi,
        "raw_advertisements": list(coordinator.raw_log),
    }
