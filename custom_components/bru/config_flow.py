"""Bluetooth discovery for a BRU Maker One."""

from __future__ import annotations

from typing import Any

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from .bru_ble.advertisement import looks_like_bru
from .const import DOMAIN


def _is_bru(discovery: BluetoothServiceInfoBleak) -> bool:
    return looks_like_bru(discovery.name, list(discovery.service_uuids))


class BruConfigFlow(ConfigFlow, domain=DOMAIN):
    """Pair a BRU machine discovered over Bluetooth."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery: BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a device found by the Bluetooth integration."""
        if not _is_bru(discovery_info):
            return self.async_abort(reason="not_supported")
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery = discovery_info
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask before creating the entry for a discovered machine."""
        assert self._discovery is not None
        name = self._discovery.name or "BRU"
        if user_input is not None:
            return self.async_create_entry(
                title=name,
                data={CONF_ADDRESS: self._discovery.address},
            )
        self.context["title_placeholders"] = {"name": name}
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": name},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick a machine that is already advertising."""
        discovered = {
            info.address: info.name or info.address
            for info in async_discovered_service_info(self.hass)
            if _is_bru(info)
        }
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=discovered.get(address, "BRU"),
                data={CONF_ADDRESS: address},
            )
        if not discovered:
            return self.async_abort(reason="no_devices_found")
        return self.async_show_form(
            step_id="user",
            data_schema=_address_schema(discovered),
        )


def _address_schema(discovered: dict[str, str]):
    import voluptuous as vol
    from homeassistant.helpers import selector

    return vol.Schema(
        {
            vol.Required(CONF_ADDRESS): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectSelectorOption(value=address, label=name)
                        for address, name in discovered.items()
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        }
    )
