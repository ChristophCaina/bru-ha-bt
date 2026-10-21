"""Brewing indicator for the BRU Maker One."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BruConfigEntry
from .const import PROMPT_SUBSTATUSES
from .coordinator import BruCoordinator


@dataclass(frozen=True, kw_only=True)
class BruPromptDescription(BinarySensorEntityDescription):
    """A prompt screen; on while the machine shows it."""

    sub_status: str


PROMPTS: tuple[BruPromptDescription, ...] = (
    BruPromptDescription(
        key="add_water",
        sub_status="msgAddWater",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:water-alert",
    ),
    BruPromptDescription(
        key="place_cup",
        sub_status="msgPlaceCup",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:cup-off-outline",
    ),
    BruPromptDescription(
        key="remove_cup",
        sub_status="msgRemoveCup",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        icon="mdi:cup",
    ),
    BruPromptDescription(
        key="close_lid",
        sub_status="msgCloseLid",
        device_class=BinarySensorDeviceClass.OPENING,
    ),
    BruPromptDescription(
        key="error",
        sub_status="msgError",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
)
assert {d.sub_status: d.key for d in PROMPTS} == PROMPT_SUBSTATUSES


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BruConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the brewing indicator and one sensor per machine prompt."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            BruBrewingBinarySensor(coordinator),
            *(BruPromptBinarySensor(coordinator, d) for d in PROMPTS),
        ]
    )


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


class BruPromptBinarySensor(BinarySensorEntity):
    """On while the machine shows a prompt. It reflects the screen, not a
    sensor: the tank can still be empty after the prompt went away."""

    _attr_has_entity_name = True
    entity_description: BruPromptDescription

    def __init__(
        self, coordinator: BruCoordinator, description: BruPromptDescription
    ) -> None:
        self.coordinator = coordinator
        self.entity_description = description
        self._attr_translation_key = description.key
        self._attr_unique_id = f"{coordinator.address}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        return self.coordinator.available

    @property
    def is_on(self) -> bool:
        return self.coordinator.state.sub_status == self.entity_description.sub_status

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
