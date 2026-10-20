"""Command frames and notification parsing."""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from datetime import date

from .status import (
    BREW_RESULT_LABELS,
    BrewResult,
    MachineState,
    temperature_byte,
    time_byte,
    water_byte,
)

OPCODE_SET_TIME = 0x08
OPCODE_GET_SETUP = 0x2A
OPCODE_SET_SETUP = 0x2C
OPCODE_BREW_START = 0x40
OPCODE_BREW_RESULT = 0x41
OPCODE_CANCEL = 0x42
OPCODE_STATUS = 0x44
OPCODE_STATUS_PAYLOAD = 0x45
OPCODE_BUTTON = 0x46
OPCODE_BUTTON_RESULT = 0x47
OPCODE_GET_PRESET = 0x50
OPCODE_UPDATE_PRESET = 0x52
OPCODE_NICKNAME = 0x4A

NAME_FIELD_BYTES = 48
NAME_CHAR_LIMIT = 12
CHECKSUM_SALT = 0x3A
APP_ID_BYTES = 8
# DIS datestamp DDMMYY. Firmware on or after this date rejects the short brew frame.
_EXTENDED_BREW_MIN = date(2026, 6, 29)


def checksum(body: bytes) -> int:
    """Checksum over every byte that precedes the checksum itself."""
    return ((-sum(body)) ^ CHECKSUM_SALT) & 0xFF


def build_frame(opcode: int, payload: bytes = b"", length: int | None = None) -> bytes:
    """Build a BRU frame. Length includes the checksum byte."""
    if length is None:
        length = 3 + len(payload) + 1
    frame = bytearray((0xFF, length & 0xFF, opcode & 0xFF))
    frame.extend(payload)
    target = length - 1
    if len(frame) < target:
        frame.extend(b"\x00" * (target - len(frame)))
    elif len(frame) > target:
        raise ValueError(
            f"Payload of {len(payload)} bytes does not fit in length {length}"
        )
    frame.append(checksum(frame))
    return bytes(frame)


def encode_name(name: str) -> bytes:
    """UTF-16LE name field: 24 code units, the app keeps the first 12."""
    trimmed = name.strip()[:NAME_CHAR_LIMIT]
    encoded = trimmed.encode("utf-16le")
    return encoded.ljust(NAME_FIELD_BYTES, b"\x00")


def build_status_request() -> bytes:
    """Ask the machine for its current status."""
    return build_frame(OPCODE_STATUS, b"", 4)


def build_cancel() -> bytes:
    """Stop the process that is currently running."""
    return build_frame(OPCODE_CANCEL, b"", 4)


def firmware_wants_extended_brew(version: str | None) -> bool:
    """True when the DIS datestamp is on or after 29 June 2026."""
    if not version:
        return False
    stamp = version.split("-", 1)[0].strip("\x00").strip()
    if len(stamp) < 6 or not stamp[:6].isdigit():
        return False
    try:
        parsed = date(2000 + int(stamp[4:6]), int(stamp[2:4]), int(stamp[0:2]))
    except ValueError:
        return False
    return parsed >= _EXTENDED_BREW_MIN


def build_brew_identity(
    name: str = "",
    tea_id: int = 0,
    app_id: bytes = b"\x00" * APP_ID_BYTES,
) -> bytes:
    """v1.10 trailer: 8-byte app id, 48-byte name, little-endian tea id."""
    if len(app_id) != APP_ID_BYTES:
        raise ValueError("Brew app id must be 8 bytes")
    return app_id + encode_name(name) + struct.pack("<I", tea_id & 0xFFFFFFFF)


def build_brew_start(
    celsius: float,
    seconds: int,
    milliliters: float,
    *,
    rinse: int = 0,
    rinse_intensity: int = 0,
    rinse_delay_seconds: int = 0,
    buzzer: bool = True,
    identity: bytes | None = None,
) -> bytes:
    """Build a start-brew frame.

    ``identity`` is the v1.10 trailer (app id, name, tea id). Firmware on or
    after 29 June 2026 rejects the frame without it.
    """
    payload = bytes(
        (
            0,
            temperature_byte(celsius),
            time_byte(seconds),
            water_byte(milliliters),
            rinse & 0xFF,
            rinse_intensity & 0xFF,
            rinse_delay_seconds & 0xFF,
            1 if buzzer else 0,
            0,
            0,
            0,
        )
    )
    if identity:
        payload += identity
    return build_frame(OPCODE_BREW_START, payload, len(payload) + 4)


def build_set_time(unix_seconds: int | None = None) -> bytes:
    """Set the machine clock. The payload is a little-endian Unix time."""
    if unix_seconds is None:
        unix_seconds = int(time.time())
    payload = struct.pack("<I", unix_seconds & 0xFFFFFFFF)
    return build_frame(OPCODE_SET_TIME, payload, 8)


def build_button_press(button_id: int) -> bytes:
    """Send a single front-panel button id."""
    return build_frame(OPCODE_BUTTON, bytes((button_id & 0xFF,)), 5)


def build_get_preset(preset_id: int) -> bytes:
    """Read one machine preset. Ids are 1 through 10."""
    if not 1 <= preset_id <= 10:
        raise ValueError("Preset id must be between 1 and 10")
    return build_frame(OPCODE_GET_PRESET, bytes((preset_id,)), 5)


def build_update_preset(
    preset_id: int,
    celsius: float,
    seconds: int,
    milliliters: float,
    name: str,
    tea_id: int | None = None,
) -> bytes:
    """Write one preset. A tea id switches the frame from 56 to 60 bytes."""
    payload = bytes(
        (
            preset_id & 0xFF,
            time_byte(seconds),
            temperature_byte(celsius),
            water_byte(milliliters),
        )
    )
    payload += encode_name(name)
    length = 56
    if tea_id is not None:
        payload += struct.pack("<I", tea_id & 0xFFFFFFFF)
        length = 60
    return build_frame(OPCODE_UPDATE_PRESET, payload, length)


def build_nickname(name: str) -> bytes:
    """Set the name stored on the machine."""
    return build_frame(OPCODE_NICKNAME, encode_name(name), 56)


def build_machine_setup(
    language: int,
    units: int,
    time_format: int,
    preset_count: int,
) -> bytes:
    """Write language, units, clock format, and how many presets are shown."""
    payload = bytes(
        (
            language & 0xFF,
            units & 0xFF,
            time_format & 0xFF,
            preset_count & 0xFF,
        )
    )
    return build_frame(OPCODE_SET_SETUP, payload, 8)


@dataclass(frozen=True)
class Notification:
    """One notify payload from the machine."""

    raw: bytes
    opcode: int
    checksum_ok: bool
    state: MachineState | None = None
    brew_result: BrewResult | None = None
    button_result: int | None = None


def parse_notification(data: bytes) -> Notification | None:
    """Decode a notify payload. Returns None when it is not a BRU frame."""
    if len(data) < 4 or data[0] != 0xFF:
        return None
    opcode = data[2]
    checksum_ok = data[-1] == checksum(data[:-1])
    state = None
    brew_result = None
    button_result = None
    if opcode == OPCODE_STATUS_PAYLOAD and len(data) >= 5:
        state = MachineState(
            status_code=data[3],
            sub_status_code=data[4],
            source="connected",
        )
    elif opcode == OPCODE_BREW_RESULT and len(data) >= 4:
        brew_result = BrewResult(code=data[3])
    elif opcode == OPCODE_BUTTON_RESULT and len(data) >= 4:
        button_result = data[3]
    return Notification(
        raw=bytes(data),
        opcode=opcode,
        checksum_ok=checksum_ok,
        state=state,
        brew_result=brew_result,
        button_result=button_result,
    )


def result_label(code: int) -> str:
    """Human readable brew result, including codes the table does not name."""
    return BREW_RESULT_LABELS.get(code, f"unknown_{code}")
