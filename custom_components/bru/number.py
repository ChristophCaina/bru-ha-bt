"""Temperature, steep time, and water amount for the next brew."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberMode, RestoreNumber
from homeassistant.const import UnitOfTemperature, UnitOfTime, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BruConfigEntry
from .bru_ble.status import (
    nearest_steep_seconds,
    nearest_temperature_c,
    nearest_water_ml,
)
from .coordinator import BruCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BruConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the three brew settings."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            BruTemperatureNumber(coordinator),
            BruSteepTimeNumber(coordinator),
            BruWaterNumber(coordinator),
        ]
    )


class _BruNumber(RestoreNumber):
    """A restored number stored on the coordinator."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: BruCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_device_info = coordinator.device_info

    async def _restore(self, fallback: float) -> None:
        last = await self.async_get_last_number_data()
        value = fallback
        if last is not None and last.native_value is not None:
            value = last.native_value
        self._store(value)
        self.async_write_ha_state()
        self.coordinator.async_notify()

    def _store(self, value: float) -> None:
        raise NotImplementedError

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._on_coordinator)
        )

    def _on_coordinator(self) -> None:
        """Pick up changes made by the tea select or the brew action."""
        value = self._coordinator_value()
        if value != self._attr_native_value:
            self._attr_native_value = value
            self.async_write_ha_state()

    def _coordinator_value(self) -> float:
        raise NotImplementedError


class BruTemperatureNumber(_BruNumber):
    """Water temperature. Values snap to the machine's steps."""

    _attr_translation_key = "temperature"
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = 0
    _attr_native_max_value = 98
    _attr_native_step = 1

    def __init__(self, coordinator: BruCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_temperature"
        self._attr_native_value = coordinator.temperature_c

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._restore(self.coordinator.temperature_c)

    def _store(self, value: float) -> None:
        snapped = nearest_temperature_c(value)
        self._attr_native_value = snapped
        self.coordinator.temperature_c = snapped

    def _coordinator_value(self) -> float:
        return self.coordinator.temperature_c

    async def async_set_native_value(self, value: float) -> None:
        self._store(value)
        self.async_write_ha_state()
        self.coordinator.async_notify()


class BruSteepTimeNumber(_BruNumber):
    """Steep time in seconds, snapped to the 10 second picker."""

    _attr_translation_key = "steep_time"
    _attr_device_class = NumberDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_native_min_value = 10
    _attr_native_max_value = 3600
    _attr_native_step = 10

    def __init__(self, coordinator: BruCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_steep_time"
        self._attr_native_value = coordinator.steep_seconds

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._restore(self.coordinator.steep_seconds)

    def _store(self, value: float) -> None:
        snapped = nearest_steep_seconds(value)
        self._attr_native_value = snapped
        self.coordinator.steep_seconds = snapped

    def _coordinator_value(self) -> float:
        return self.coordinator.steep_seconds

    async def async_set_native_value(self, value: float) -> None:
        self._store(value)
        self.async_write_ha_state()
        self.coordinator.async_notify()


class BruWaterNumber(_BruNumber):
    """Water volume. 25 ml steps include the newer firmware amounts."""

    _attr_translation_key = "water"
    _attr_device_class = NumberDeviceClass.VOLUME
    _attr_native_unit_of_measurement = UnitOfVolume.MILLILITERS
    _attr_native_min_value = 50
    _attr_native_max_value = 350
    _attr_native_step = 25

    def __init__(self, coordinator: BruCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_water"
        self._attr_native_value = coordinator.water_ml

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._restore(self.coordinator.water_ml)

    def _store(self, value: float) -> None:
        snapped = nearest_water_ml(value)
        self._attr_native_value = snapped
        self.coordinator.water_ml = snapped

    def _coordinator_value(self) -> float:
        return self.coordinator.water_ml

    async def async_set_native_value(self, value: float) -> None:
        self._store(value)
        self.async_write_ha_state()
        self.coordinator.async_notify()
