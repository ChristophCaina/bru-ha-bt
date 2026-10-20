"""Status sensor for the BRU Maker One."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BruConfigEntry
from .coordinator import BruCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BruConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the status sensor."""
    async_add_entities([BruStatusSensor(entry.runtime_data)])


class BruStatusSensor(SensorEntity):
    """Shows the latest advertised or connected machine state."""

    _attr_has_entity_name = True
    _attr_translation_key = "status"
    _attr_icon = "mdi:tea"

    def __init__(self, coordinator: BruCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.address}_status"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> str:
        return self.coordinator.state.label

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        state = self.coordinator.state
        return {
            "status": state.status,
            "sub_status": state.sub_status,
            "status_code": state.status_code,
            "sub_status_code": state.sub_status_code,
            "source": state.source,
            "busy": state.busy,
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
