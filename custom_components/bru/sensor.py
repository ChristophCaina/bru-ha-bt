"""Status sensor for the BRU Maker One."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BruConfigEntry
from .coordinator import BruCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BruConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the status and signal sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            BruStatusSensor(coordinator),
            BruSteepingSinceSensor(coordinator),
            BruReadyAtSensor(coordinator),
            BruRssiSensor(coordinator),
        ]
    )


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
    def available(self) -> bool:
        return self.coordinator.available

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


class _BruTimestampSensor(SensorEntity):
    """A timestamp the frontend shows as a relative time ("in 2 minutes")."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: BruCoordinator, key: str) -> None:
        self.coordinator = coordinator
        self._attr_translation_key = key
        self._attr_unique_id = f"{coordinator.address}_{key}"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        return self.coordinator.available

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class BruSteepingSinceSensor(_BruTimestampSensor):
    """When the current steep started. Empty when not brewing."""

    _attr_icon = "mdi:timer-sand"

    def __init__(self, coordinator: BruCoordinator) -> None:
        super().__init__(coordinator, "steeping_since")

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.steeping_since


class BruReadyAtSensor(_BruTimestampSensor):
    """When the steep ends. Only known for brews started from Home Assistant."""

    _attr_icon = "mdi:timer-check-outline"

    def __init__(self, coordinator: BruCoordinator) -> None:
        super().__init__(coordinator, "ready_at")

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.ready_at
