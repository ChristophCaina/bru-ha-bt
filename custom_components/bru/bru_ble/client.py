"""Bleak session for one BRU Maker One."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .advertisement import DiscoveredMachine, parse_advertisement
from .commands import (
    OPCODE_BREW_RESULT,
    OPCODE_STATUS_PAYLOAD,
    Notification,
    build_brew_start,
    build_cancel,
    build_set_time,
    build_status_request,
    parse_notification,
)
from .errors import BrewRejected, MachineNotFound, PairingFailed, ResponseTimeout
from .status import BrewResult, MachineState
from .uuids import FIRMWARE_REVISION, NOTIFY_UUID, WRITE_UUID

_LOGGER = logging.getLogger(__name__)

COMMAND_TIMEOUT = 8.0
PAIR_TIMEOUT = 45.0
NOTICE_AFTER = 1.0

_PAIRING_HINT = (
    "The machine is not bonded. Put it in pairing mode (Machine Setup, "
    "Pair New Device) until it shows Waiting for connection. The ESPHome "
    "proxy that keeps the bond needs the bru_bond component, so it starts "
    "encryption when the link opens and accepts the code."
)


def _needs_bond(exc: BaseException) -> bool:
    """True when a GATT error means the link is not authenticated yet."""
    text = str(exc).lower()
    return (
        "insufficient authentication" in text or "insufficient encryption" in text
    )


def _already_bonded(exc: BaseException) -> bool:
    """BlueZ raises this when the controller already has the bond."""
    compact = str(exc).lower().replace(" ", "")
    return "alreadyexists" in compact or "alreadypaired" in compact


class BruClient:
    """Short-lived connection used the same way as the app.

    Connect, write one command, read the notify, disconnect. The first
    contact has to happen while the machine shows ``Waiting for connection``
    so the host can complete numeric-comparison bonding.
    """

    def __init__(self, device: Any, on_pairing: Any = None) -> None:
        """``device`` is a Bluetooth address or a Bleak ``BLEDevice``.

        ``on_pairing`` is called on the running loop just before ``pair()``,
        so a UI can tell the user to confirm the code while the call blocks.
        """
        self._device = device
        self._on_pairing = on_pairing
        self._client: Any = None
        self._queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=32)
        self._loop: asyncio.AbstractEventLoop | None = None
        self.firmware_version: str | None = None
        self.state = MachineState(source="none")

    async def __aenter__(self) -> BruClient:
        await self.connect()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.disconnect()

    async def connect(self) -> None:
        """Open the GATT link and subscribe to notifications."""
        from bleak import BleakClient

        self._loop = asyncio.get_running_loop()
        self._client = BleakClient(self._device)
        await self._client.connect()
        # Pair before any GATT write. A refused notify makes the machine drop
        # the link, and the pairing request afterwards never starts.
        await self._pair()
        try:
            await self._client.start_notify(NOTIFY_UUID, self._on_notify)
        except Exception as exc:
            if _needs_bond(exc):
                raise PairingFailed(f"{_PAIRING_HINT} ({exc})") from exc
            raise
        self.firmware_version = await self._read_firmware()
        try:
            await self._write(build_set_time())
        except Exception:
            _LOGGER.warning(
                "setTime was rejected. If this is the first connection, "
                "confirm the pairing code on the machine."
            )

    async def disconnect(self) -> None:
        """Drop the link. Safe to call when already disconnected."""
        client = self._client
        self._client = None
        if client is not None and client.is_connected:
            await client.disconnect()

    async def _pair(self) -> None:
        """Bond on this connection. A fast return means the bond already exists."""
        task = asyncio.ensure_future(self._client.pair())
        try:
            await asyncio.wait_for(asyncio.shield(task), NOTICE_AFTER)
        except TimeoutError:
            if self._on_pairing is not None:
                self._on_pairing()
            try:
                await asyncio.wait_for(task, PAIR_TIMEOUT - NOTICE_AFTER)
            except TimeoutError as exc:
                task.cancel()
                raise PairingFailed(f"{_PAIRING_HINT} ({exc})") from exc
            except Exception as exc:
                self._raise_pair(exc)
        except Exception as exc:
            self._raise_pair(exc)

    def _raise_pair(self, exc: BaseException) -> None:
        if _already_bonded(exc):
            return
        _LOGGER.warning("BRU pairing failed: %s", exc)
        if isinstance(exc, NotImplementedError):
            raise PairingFailed(
                "This Bluetooth path cannot pair. Upgrade the ESPHome proxy, "
                "or connect with the Home Assistant Bluetooth adapter."
            ) from exc
        raise PairingFailed(f"{_PAIRING_HINT} ({exc})") from exc

    def _on_notify(self, _sender: Any, data: bytearray) -> None:
        if self._loop is None:
            return
        payload = bytes(data)
        self._loop.call_soon_threadsafe(self._enqueue, payload)

    def _enqueue(self, payload: bytes) -> None:
        parsed = parse_notification(payload)
        if parsed and parsed.state is not None:
            self.state = parsed.state
        if self._queue.full():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                return
        self._queue.put_nowait(payload)

    async def _write(self, frame: bytes) -> None:
        if self._client is None or not self._client.is_connected:
            raise MachineNotFound("Not connected to a BRU machine")
        await self._client.write_gatt_char(WRITE_UUID, frame, response=True)

    async def _read_firmware(self) -> str | None:
        try:
            raw = await self._client.read_gatt_char(FIRMWARE_REVISION)
        except Exception:
            return None
        text = raw.decode("utf-8", errors="replace").strip("\x00").strip()
        return text or None

    def _drain(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                return

    async def _wait(self, opcodes: set[int], timeout: float) -> Notification:
        """Wait until a notification with one of ``opcodes`` arrives."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise ResponseTimeout(
                    f"No response for opcodes {sorted(hex(op) for op in opcodes)}"
                )
            try:
                payload = await asyncio.wait_for(self._queue.get(), remaining)
            except TimeoutError as exc:
                raise ResponseTimeout(
                    f"No response for opcodes {sorted(hex(op) for op in opcodes)}"
                ) from exc
            parsed = parse_notification(payload)
            if parsed is not None and parsed.opcode in opcodes:
                return parsed

    async def read_status(self) -> MachineState:
        """Request a status notification and return it."""
        self._drain()
        await self._write(build_status_request())
        note = await self._wait({OPCODE_STATUS_PAYLOAD}, COMMAND_TIMEOUT)
        if note.state is None:
            raise ResponseTimeout("Status response had no state bytes")
        self.state = note.state
        return note.state

    async def start_brew(
        self,
        celsius: float,
        seconds: int,
        milliliters: float,
        *,
        rinse: int = 0,
        buzzer: bool = True,
    ) -> BrewResult:
        """Send a brew and wait for the 0x41 result. Raises if it is refused."""
        frame = build_brew_start(
            celsius,
            seconds,
            milliliters,
            rinse=rinse,
            buzzer=buzzer,
        )
        self._drain()
        await self._write(frame)
        note = await self._wait({OPCODE_BREW_RESULT}, COMMAND_TIMEOUT)
        result = note.brew_result or BrewResult(code=-1)
        if not result.success:
            raise BrewRejected(result.code, result.label)
        return result

    async def cancel(self) -> None:
        """Ask the machine to stop the current process."""
        await self._write(build_cancel())


async def discover(timeout: float = 8.0) -> list[DiscoveredMachine]:
    """Scan for BRU advertisements. Bonded machines may use a private address."""
    from bleak import BleakScanner

    discovered = await BleakScanner.discover(timeout=timeout, return_adv=True)
    found: list[DiscoveredMachine] = []
    for device, advertisement in discovered.values():
        name = advertisement.local_name or device.name
        parsed = parse_advertisement(
            device.address,
            name,
            rssi=advertisement.rssi,
            manufacturer_data=dict(advertisement.manufacturer_data),
            service_data={
                str(key): value for key, value in advertisement.service_data.items()
            },
            service_uuids=list(advertisement.service_uuids or []),
        )
        if parsed is not None:
            found.append(parsed)
    return found
