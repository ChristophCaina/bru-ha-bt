"""Brewing indicator for the BRU Maker One."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BruConfigEntry
from .coordinator import BruCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BruConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the brewing indicator."""
    async_add_entities([BruBrewingBinarySensor(entry.runtime_data)])


class BruBrewingBinarySensor(BinarySensorEntity):
    """On from filling until the tea is ready (or the brew is cancelled)."""

    _attr_has_entity_name = True
    _attr_translation_key = "brewing"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: BruCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.address}_brewing"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        return self.coordinator.available

    @property
    def is_on(self) -> bool:
        return self.coordinator.brewing

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
