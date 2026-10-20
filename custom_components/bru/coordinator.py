"""Live state for one BRU machine."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothCallbackMatcher,
    BluetoothChange,
    BluetoothServiceInfoBleak,
)
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo

from .bru_ble.advertisement import parse_advertisement
from .bru_ble.client import BruClient
from .bru_ble.errors import BruError
from .bru_ble.status import MachineState
from .const import (
    DEFAULT_STEEP_SECONDS,
    DEFAULT_TEMPERATURE_C,
    DEFAULT_WATER_ML,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class BruCoordinator:
    """Tracks advertisements and opens a connection only to send a command."""

    def __init__(self, hass: HomeAssistant, entry: Any) -> None:
        self.hass = hass
        self.entry = entry
        self.address: str = entry.data[CONF_ADDRESS]
        self.state = MachineState(source="none")
        self.temperature_c = DEFAULT_TEMPERATURE_C
        self.steep_seconds = DEFAULT_STEEP_SECONDS
        self.water_ml = DEFAULT_WATER_ML
        self._listeners: list[Callable[[], None]] = []
        self._unsub: Callable[[], None] | None = None
        self._lock = asyncio.Lock()
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, self.address)},
            connections={(CONNECTION_BLUETOOTH, self.address)},
            manufacturer="BRU",
            model="Maker One",
            name=entry.title or "BRU Maker One",
        )

    async def async_start(self) -> None:
        """Subscribe to advertisements and apply the newest one we already saw."""
        info = bluetooth.async_last_service_info(self.hass, self.address)
        if info is not None:
            self._apply(info)
        self._unsub = bluetooth.async_register_callback(
            self.hass,
            self._on_advertisement,
            BluetoothCallbackMatcher(address=self.address),
            BluetoothChange.ADVERTISEMENT,
        )

    def async_stop(self) -> None:
        """Drop the advertisement subscription."""
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    def async_add_listener(
        self, update_callback: Callable[[], None]
    ) -> Callable[[], None]:
        """Register an entity callback. Returns the unsubscribe function."""
        self._listeners.append(update_callback)

        def _remove() -> None:
            if update_callback in self._listeners:
                self._listeners.remove(update_callback)

        return _remove

    @callback
    def _on_advertisement(
        self,
        service_info: BluetoothServiceInfoBleak,
        _change: BluetoothChange,
    ) -> None:
        self._apply(service_info)
        self._publish()

    def _apply(self, service_info: BluetoothServiceInfoBleak) -> None:
        parsed = parse_advertisement(
            service_info.address,
            service_info.name,
            rssi=service_info.rssi,
            manufacturer_data=dict(service_info.manufacturer_data),
            service_data=dict(service_info.service_data),
            service_uuids=list(service_info.service_uuids),
        )
        if parsed is not None and parsed.state is not None:
            self.state = parsed.state

    def _publish(self) -> None:
        for listener in list(self._listeners):
            listener()

    async def _connect(self) -> BruClient:
        device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if device is None:
            raise BruError(
                "BRU machine is not in range. For a first bond, put it in "
                "pairing mode (Machine Setup, Pair New Device)."
            )
        client = BruClient(device)
        await client.connect()
        return client

    async def async_start_brew(self) -> None:
        """Connect, start a brew with the current settings, then disconnect."""
        async with self._lock:
            client = await self._connect()
            try:
                await client.start_brew(
                    self.temperature_c,
                    self.steep_seconds,
                    self.water_ml,
                )
                try:
                    self.state = await client.read_status()
                except BruError:
                    _LOGGER.debug("Status read after brew start failed", exc_info=True)
            finally:
                await client.disconnect()
            self._publish()

    async def async_cancel_brew(self) -> None:
        """Connect, send cancel, then disconnect."""
        async with self._lock:
            client = await self._connect()
            try:
                await client.cancel()
                try:
                    self.state = await client.read_status()
                except BruError:
                    _LOGGER.debug("Status read after cancel failed", exc_info=True)
            finally:
                await client.disconnect()
            self._publish()
