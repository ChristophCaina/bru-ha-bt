"""Brew lifecycle events for the BRU Maker One."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BruConfigEntry
from .const import BREW_EVENT_TYPES
from .coordinator import BruCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BruConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the brew event entity."""
    async_add_entities([BruBrewEvent(entry.runtime_data)])


class BruBrewEvent(EventEntity):
    """Fires brew_started, brew_finished, and brew_cancelled."""

    _attr_has_entity_name = True
    _attr_translation_key = "brew"
    _attr_event_types = BREW_EVENT_TYPES

    def __init__(self, coordinator: BruCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.address}_brew_event"
        self._attr_device_info = coordinator.device_info

    @callback
    def _on_event(self, event_type: str) -> None:
        self._trigger_event(
            event_type,
            {
                "temperature_c": self.coordinator.temperature_c,
                "steep_seconds": self.coordinator.steep_seconds,
                "water_ml": self.coordinator.water_ml,
            },
        )
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.async_add_event_listener(self._on_event))
