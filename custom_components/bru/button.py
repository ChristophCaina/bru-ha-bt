"""Start and cancel buttons."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BruConfigEntry
from .bru_ble.errors import BruError
from .coordinator import BruCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BruConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the brew controls."""
    coordinator = entry.runtime_data
    async_add_entities(
        [BruStartButton(coordinator), BruCancelButton(coordinator)]
    )


class _BruButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: BruCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_device_info = coordinator.device_info


class BruStartButton(_BruButton):
    """Start a brew with the current temperature, time, and water amount."""

    _attr_translation_key = "start_brew"
    _attr_icon = "mdi:play"

    def __init__(self, coordinator: BruCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_start_brew"

    async def async_press(self) -> None:
        try:
            await self.coordinator.async_start_brew()
        except BruError as err:
            raise HomeAssistantError(str(err)) from err


class BruCancelButton(_BruButton):
    """Stop the process that is currently running."""

    _attr_translation_key = "cancel_brew"
    _attr_icon = "mdi:stop"

    def __init__(self, coordinator: BruCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_cancel_brew"

    async def async_press(self) -> None:
        try:
            await self.coordinator.async_cancel_brew()
        except BruError as err:
            raise HomeAssistantError(str(err)) from err
