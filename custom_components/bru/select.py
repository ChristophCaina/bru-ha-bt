"""Tea selection for the BRU Maker One."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import BruConfigEntry
from .coordinator import BruCoordinator
from .teas import MANUAL


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BruConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the tea select."""
    async_add_entities([BruTeaSelect(entry.runtime_data)])


class BruTeaSelect(SelectEntity, RestoreEntity):
    """Loads temperature and steep time for a tea. Shows manual after edits."""

    _attr_has_entity_name = True
    _attr_translation_key = "tea"
    _attr_icon = "mdi:tea-outline"

    def __init__(self, coordinator: BruCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.address}_tea"
        self._attr_device_info = coordinator.device_info
        self._attr_options = [MANUAL, *coordinator.teas]

    @property
    def current_option(self) -> str:
        return self.coordinator.current_tea

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        tea = self.coordinator.teas.get(self.coordinator.current_tea)
        if tea is None:
            return {}
        return {
            "temperature_c": tea.temperature_c,
            "steep_seconds": tea.steep_seconds,
            "water_ml": tea.water_ml,
            "builtin": tea.builtin,
        }

    async def async_select_option(self, option: str) -> None:
        self.coordinator.select_tea(option)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state in self.coordinator.teas:
            # Only remember the choice; the restored numbers decide whether
            # it still matches.
            self.coordinator.selected_tea = last.state
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
