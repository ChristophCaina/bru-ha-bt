"""Live state for one BRU machine."""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timedelta
import logging
from typing import Any, Callable

from homeassistant.components import bluetooth, persistent_notification
from homeassistant.components.bluetooth import (
    BluetoothCallbackMatcher,
    BluetoothChange,
    BluetoothServiceInfoBleak,
)
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.util import dt as dt_util

from .bru_ble.advertisement import parse_advertisement
from .bru_ble.client import BruClient
from .bru_ble.errors import BruError
from .bru_ble.status import MachineState
from .const import (
    BREW_CANCELLED,
    BREW_FINISHED,
    BREW_STARTED,
    DEFAULT_STEEP_SECONDS,
    EVENT_BREW,
    DEFAULT_TEMPERATURE_C,
    DEFAULT_WATER_ML,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

RAW_LOG_SIZE = 300
# A brew started from HA must reach steeping within this window for its
# steep time to be used for ready_at.
HA_START_WINDOW = timedelta(minutes=10)


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
        self._unsub: list[Callable[[], None]] = []
        self.available = False
        self.rssi: int | None = None
        self._busy = False
        self._cancel_requested = False
        self._event_listeners: list[Callable[[str], None]] = []
        # Steep timing. ready_at is only known for brews started from HA,
        # because the machine does not advertise the configured steep time.
        self.steeping_since: datetime | None = None
        self.ready_at: datetime | None = None
        self._brew_steep_seconds: int | None = None
        self._brew_started_at: datetime | None = None
        # Advertisement payloads, recorded only when the bytes change.
        self.raw_log: deque[dict[str, Any]] = deque(maxlen=RAW_LOG_SIZE)
        self._last_raw: tuple[Any, Any] | None = None
        self._last_raw_time: datetime | None = None
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
            self.available = True
            self._apply(info)
            # Seed the busy flag so a running brew at startup does not
            # produce a spurious brew_started event.
            self._busy = self.brewing
        self._unsub.append(
            bluetooth.async_register_callback(
                self.hass,
                self._on_advertisement,
                BluetoothCallbackMatcher(address=self.address),
                BluetoothChange.ADVERTISEMENT,
            )
        )
        self._unsub.append(
            bluetooth.async_track_unavailable(
                self.hass, self._on_unavailable, self.address, connectable=False
            )
        )

    def async_stop(self) -> None:
        """Drop the advertisement and availability subscriptions."""
        while self._unsub:
            self._unsub.pop()()

    def async_add_listener(
        self, update_callback: Callable[[], None]
    ) -> Callable[[], None]:
        """Register an entity callback. Returns the unsubscribe function."""
        self._listeners.append(update_callback)

        def _remove() -> None:
            if update_callback in self._listeners:
                self._listeners.remove(update_callback)

        return _remove

    def async_add_event_listener(
        self, event_callback: Callable[[str], None]
    ) -> Callable[[], None]:
        """Register a callback for brew lifecycle events."""
        self._event_listeners.append(event_callback)

        def _remove() -> None:
            if event_callback in self._event_listeners:
                self._event_listeners.remove(event_callback)

        return _remove

    @callback
    def _on_advertisement(
        self,
        service_info: BluetoothServiceInfoBleak,
        _change: BluetoothChange,
    ) -> None:
        self.available = True
        self._apply(service_info)
        self._track_brew()
        self._publish()

    @callback
    def _on_unavailable(self, _service_info: BluetoothServiceInfoBleak) -> None:
        """The machine stopped advertising (off, or out of range)."""
        _LOGGER.debug("BRU %s is no longer advertising", self.address)
        self.available = False
        self._publish()

    @property
    def brewing(self) -> bool:
        """True while a brew is running and the tea is not ready yet.

        The main status stays Brewing on the "Ready to enjoy" screen, so
        state.busy alone would only drop once the cup is taken away.
        """
        return self.state.busy and self.state.sub_status != "brewingEnjoy"

    def _track_brew(self) -> None:
        """Turn brewing/idle transitions into brew lifecycle events."""
        busy = self.brewing
        self._track_steeping(busy)
        if busy == self._busy:
            return
        self._busy = busy
        if busy:
            self._cancel_requested = False
            self._fire(BREW_STARTED)
        else:
            self._fire(BREW_CANCELLED if self._cancel_requested else BREW_FINISHED)
            self._cancel_requested = False
            self._brew_steep_seconds = None
            self._brew_started_at = None

    def _track_steeping(self, busy: bool) -> None:
        """Remember when steeping started and when the tea should be ready."""
        if not busy:
            self.steeping_since = None
            self.ready_at = None
            return
        if self.state.sub_status != "brewingSteeping" or self.steeping_since:
            return
        self.steeping_since = dt_util.utcnow()
        if (
            self._brew_steep_seconds is not None
            and self._brew_started_at is not None
            and self.steeping_since - self._brew_started_at <= HA_START_WINDOW
        ):
            self.ready_at = self.steeping_since + timedelta(
                seconds=self._brew_steep_seconds
            )
        _LOGGER.debug(
            "BRU %s: steeping since %s, ready at %s",
            self.address,
            self.steeping_since,
            self.ready_at,
        )

    def _record_raw(self, service_info: BluetoothServiceInfoBleak) -> None:
        """Keep advertisement payloads whose bytes changed, for protocol work."""
        manufacturer = {
            str(cid): bytes(data).hex() for cid, data in service_info.manufacturer_data.items()
        }
        service = {
            uuid: bytes(data).hex() for uuid, data in service_info.service_data.items()
        }
        key = (tuple(sorted(manufacturer.items())), tuple(sorted(service.items())))
        if key == self._last_raw:
            return
        now = dt_util.utcnow()
        delta = (
            round((now - self._last_raw_time).total_seconds(), 1)
            if self._last_raw_time
            else None
        )
        self._last_raw = key
        self._last_raw_time = now
        entry = {
            "time": now.isoformat(),
            "delta_s": delta,
            "manufacturer_data": manufacturer,
            "service_data": service,
            "status": self.state.status,
            "sub_status": self.state.sub_status,
            "rssi": service_info.rssi,
        }
        self.raw_log.append(entry)
        _LOGGER.debug(
            "BRU %s raw advert (+%ss) %s/%s mfr=%s svc=%s",
            self.address,
            delta,
            self.state.status,
            self.state.sub_status,
            manufacturer,
            service,
        )

    def _fire(self, event_type: str) -> None:
        _LOGGER.debug("BRU %s: %s", self.address, event_type)
        self.hass.bus.async_fire(
            EVENT_BREW,
            {
                "device_id": self.device_id,
                "address": self.address,
                "type": event_type,
                "temperature_c": self.temperature_c,
                "steep_seconds": self.steep_seconds,
                "water_ml": self.water_ml,
            },
        )
        for listener in list(self._event_listeners):
            listener(event_type)

    @property
    def device_id(self) -> str | None:
        """Device registry id, for event payloads."""
        device = dr.async_get(self.hass).async_get_device(
            identifiers={(DOMAIN, self.address)}
        )
        return device.id if device else None

    def _apply(self, service_info: BluetoothServiceInfoBleak) -> None:
        parsed = parse_advertisement(
            service_info.address,
            service_info.name,
            rssi=service_info.rssi,
            manufacturer_data=dict(service_info.manufacturer_data),
            service_data=dict(service_info.service_data),
            service_uuids=list(service_info.service_uuids),
        )
        self.rssi = service_info.rssi
        if parsed is not None and parsed.state is not None:
            self.state = parsed.state
        self._record_raw(service_info)

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
        notice = f"bru_pairing_{self.address}"

        def _on_pairing() -> None:
            persistent_notification.async_create(
                self.hass,
                "Confirm the code on the BRU. It must show Waiting for connection "
                "(Machine Setup, Pair New Device). If no code appears in Home "
                "Assistant, this link is an ESPHome Bluetooth proxy that cannot "
                "do numeric comparison.",
                title="BRU pairing",
                notification_id=notice,
            )

        client = BruClient(device, on_pairing=_on_pairing)
        try:
            await client.connect()
        finally:
            persistent_notification.async_dismiss(self.hass, notice)
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
                self._brew_steep_seconds = int(self.steep_seconds)
                self._brew_started_at = dt_util.utcnow()
                try:
                    self.state = await client.read_status()
                except BruError:
                    _LOGGER.debug("Status read after brew start failed", exc_info=True)
            finally:
                await client.disconnect()
            self._track_brew()
            self._publish()

    async def async_cancel_brew(self) -> None:
        """Connect, send cancel, then disconnect."""
        async with self._lock:
            client = await self._connect()
            try:
                await client.cancel()
                self._cancel_requested = True
                try:
                    self.state = await client.read_status()
                except BruError:
                    _LOGGER.debug("Status read after cancel failed", exc_info=True)
            finally:
                await client.disconnect()
            self._track_brew()
            self._publish()
