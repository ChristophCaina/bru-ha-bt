"""Status sensor for the BRU Maker One."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BruConfigEntry
from .bru_ble.status import state_key, state_options
from .coordinator import BruCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BruConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the status and signal sensors."""
    coordinator = entry.runtime_data
    async_add_entities([BruStatusSensor(coordinator), BruRssiSensor(coordinator)])


class BruStatusSensor(SensorEntity):
    """Shows the latest advertised or connected machine state."""

    _attr_has_entity_name = True
    _attr_translation_key = "status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_icon = "mdi:tea"

    def __init__(self, coordinator: BruCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.address}_status"
        self._attr_device_info = coordinator.device_info

    @property
    def options(self) -> list[str]:
        """States the automation editor can offer in a dropdown."""
        return state_options(self.coordinator.state.label)

    @property
    def available(self) -> bool:
        return self.coordinator.available

    @property
    def native_value(self) -> str:
        return state_key(self.coordinator.state.label)

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


class BruRssiSensor(SensorEntity):
    """Signal strength of the latest advertisement."""

    _attr_has_entity_name = True
    _attr_translation_key = "rssi"
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: BruCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.address}_rssi"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        return self.coordinator.available and self.coordinator.rssi is not None

    @property
    def native_value(self) -> int | None:
        return self.coordinator.rssi

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
