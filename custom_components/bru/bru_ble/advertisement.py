"""Advertisement parsing for BRU machines."""

from __future__ import annotations

from dataclasses import dataclass

from .status import STATUS_NAMES, MachineState
from .uuids import DFU_NAME_PREFIXES, NAME_TOKEN, SERVICE_UUID


@dataclass(frozen=True)
class DiscoveredMachine:
    """A BRU advertisement, with state when the manufacturer bytes parse."""

    address: str
    name: str | None
    rssi: int | None
    state: MachineState | None


def looks_like_bru(name: str | None, service_uuids: list[str] | None = None) -> bool:
    """True for a normal BRU advert, false for a DFU advert."""
    lowered = (name or "").lower()
    if any(lowered.startswith(prefix) for prefix in DFU_NAME_PREFIXES):
        return False
    if name and NAME_TOKEN in name.upper():
        return True
    if service_uuids:
        return any(uuid.lower() == SERVICE_UUID for uuid in service_uuids)
    return False


def state_from_bytes(raw: bytes | None, source: str) -> MachineState | None:
    """Read status at byte 3 and sub-status at byte 4."""
    if raw is None or len(raw) < 5:
        return None
    return MachineState(
        status_code=raw[3],
        sub_status_code=raw[4],
        source=source,
    )


def _state_from_manufacturer(
    manufacturer_data: dict[int, bytes] | None,
) -> MachineState | None:
    """Pick the manufacturer record whose status byte is a known BRU state."""
    if not manufacturer_data:
        return None
    fallback = None
    for company_id, payload in manufacturer_data.items():
        state = state_from_bytes(
            manufacturer_buffer(company_id, payload), "advertising"
        )
        if state is None:
            continue
        if state.status_code in STATUS_NAMES:
            return state
        fallback = state
    return fallback


def manufacturer_buffer(company_id: int, payload: bytes) -> bytes:
    """Rebuild the buffer the app sees, including the company id."""
    return company_id.to_bytes(2, "little") + payload


def parse_advertisement(
    address: str,
    name: str | None,
    *,
    rssi: int | None = None,
    manufacturer_data: dict[int, bytes] | None = None,
    service_data: dict[str, bytes] | None = None,
    service_uuids: list[str] | None = None,
) -> DiscoveredMachine | None:
    """Parse one advertisement. Returns None when it is not a BRU machine."""
    if not looks_like_bru(name, service_uuids):
        # Service data for our UUID is enough even when the name is hidden.
        if not service_data or not any(
            key.lower() == SERVICE_UUID for key in service_data
        ):
            return None

    state = _state_from_manufacturer(manufacturer_data)
    if state is None and service_data:
        for key, payload in service_data.items():
            if key.lower() == SERVICE_UUID:
                state = state_from_bytes(payload, "advertising")
                break
    return DiscoveredMachine(address=address, name=name, rssi=rssi, state=state)
