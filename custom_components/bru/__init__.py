"""Config entry setup for the BRU Maker One."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import BruCoordinator
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.EVENT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
]

type BruConfigEntry = ConfigEntry[BruCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the brew action."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: BruConfigEntry) -> bool:
    """Set up a bonded BRU machine from a config entry."""
    coordinator = BruCoordinator(hass, entry)
    await coordinator.async_start()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: BruConfigEntry) -> None:
    """Custom teas changed: rebuild the select options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: BruConfigEntry) -> bool:
    """Stop advertisement updates and unload entities."""
    coordinator: BruCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
    coordinator.async_stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
