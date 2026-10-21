"""The bru.brew action."""

from __future__ import annotations

from bleak.exc import BleakError
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr
import voluptuous as vol

from .bru_ble.errors import BruError
from .const import DOMAIN, SERVICE_BREW

ATTR_DEVICE_ID = "device_id"
ATTR_TEA = "tea"
ATTR_TEMPERATURE = "temperature"
ATTR_STEEP_TIME = "steep_time"
ATTR_WATER = "water"

BREW_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Optional(ATTR_TEA): cv.string,
        vol.Optional(ATTR_TEMPERATURE): vol.All(vol.Coerce(int), vol.Range(0, 98)),
        vol.Optional(ATTR_STEEP_TIME): vol.All(cv.time_period, cv.positive_timedelta),
        vol.Optional(ATTR_WATER): vol.All(vol.Coerce(int), vol.Range(50, 350)),
    }
)


def _coordinator_for(hass: HomeAssistant, device_id: str):
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        raise ServiceValidationError(f"Unknown device {device_id}")
    for entry_id in device.config_entries:
        entry = hass.config_entries.async_get_entry(entry_id)
        if (
            entry is not None
            and entry.domain == DOMAIN
            and entry.state is ConfigEntryState.LOADED
        ):
            return entry.runtime_data
    raise ServiceValidationError(f"{device.name} is not a loaded BRU machine")


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register bru.brew once for all machines."""

    async def _brew(call: ServiceCall) -> None:
        coordinator = _coordinator_for(hass, call.data[ATTR_DEVICE_ID])
        tea = call.data.get(ATTR_TEA)
        if tea is not None:
            if tea not in coordinator.teas:
                raise ServiceValidationError(
                    f"Unknown tea {tea}. Known: {', '.join(coordinator.teas)}"
                )
            coordinator.select_tea(tea)
        steep = call.data.get(ATTR_STEEP_TIME)
        coordinator.apply_settings(
            temperature_c=call.data.get(ATTR_TEMPERATURE),
            steep_seconds=steep.total_seconds() if steep is not None else None,
            water_ml=call.data.get(ATTR_WATER),
        )
        try:
            await coordinator.async_start_brew()
        except (BruError, BleakError) as err:
            raise HomeAssistantError(str(err)) from err

    hass.services.async_register(DOMAIN, SERVICE_BREW, _brew, schema=BREW_SCHEMA)
