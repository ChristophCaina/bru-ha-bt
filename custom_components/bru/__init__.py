"""Config entry setup for the BRU Maker One."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import BruCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.EVENT,
    Platform.NUMBER,
    Platform.SENSOR,
]

type BruConfigEntry = ConfigEntry[BruCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: BruConfigEntry) -> bool:
    """Set up a bonded BRU machine from a config entry."""
    coordinator = BruCoordinator(hass, entry)
    await coordinator.async_start()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BruConfigEntry) -> bool:
    """Stop advertisement updates and unload entities."""
    coordinator: BruCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
    coordinator.async_stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
