"""Availability and brew lifecycle events, run against a real Home Assistant core."""

from __future__ import annotations

from datetime import timedelta

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import callback  # noqa: E402
from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: E402

from custom_components.bru.bru_ble.status import MachineState  # noqa: E402
from custom_components.bru.const import (  # noqa: E402
    BREW_CANCELLED,
    BREW_FINISHED,
    BREW_STARTED,
    DOMAIN,
    EVENT_BREW,
)
from custom_components.bru.coordinator import BruCoordinator  # noqa: E402

ADDRESS = "AA:BB:CC:DD:EE:FF"
IDLE = MachineState(status_code=1, sub_status_code=4, source="adv")  # homeScreen
STEEPING = MachineState(status_code=5, sub_status_code=26, source="adv")
FILLING = MachineState(status_code=5, sub_status_code=25, source="adv")
ENJOY = MachineState(status_code=5, sub_status_code=30, source="adv")  # brewingEnjoy


@pytest.fixture
def coordinator(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={"address": ADDRESS}, title="BRU")
    entry.add_to_hass(hass)
    return BruCoordinator(hass, entry)


def _collect(hass, coordinator):
    bus, direct = [], []
    hass.bus.async_listen(EVENT_BREW, callback(lambda e: bus.append(e.data["type"])))
    coordinator.async_add_event_listener(direct.append)
    return bus, direct


async def test_brew_started_and_finished(hass, coordinator):
    bus, direct = _collect(hass, coordinator)
    for state in (IDLE, STEEPING, STEEPING, ENJOY, IDLE):
        coordinator.state = state
        coordinator._track_brew()
    await hass.async_block_till_done()
    assert direct == [BREW_STARTED, BREW_FINISHED]
    assert bus == [BREW_STARTED, BREW_FINISHED]


async def test_cancel_is_reported_as_cancelled(hass, coordinator):
    bus, direct = _collect(hass, coordinator)
    coordinator.state = STEEPING
    coordinator._track_brew()
    coordinator._cancel_requested = True
    coordinator.state = IDLE
    coordinator._track_brew()
    # A later, normal brew is reported as finished again.
    coordinator.state = STEEPING
    coordinator._track_brew()
    coordinator.state = ENJOY
    coordinator._track_brew()
    await hass.async_block_till_done()
    assert direct == [BREW_STARTED, BREW_CANCELLED, BREW_STARTED, BREW_FINISHED]


async def test_enjoy_screen_counts_as_finished(hass, coordinator):
    _, direct = _collect(hass, coordinator)
    coordinator.state = STEEPING
    coordinator._track_brew()
    assert coordinator.brewing
    coordinator.state = ENJOY
    coordinator._track_brew()
    assert not coordinator.brewing
    assert coordinator.state.busy  # main status is still Brewing
    assert direct == [BREW_STARTED, BREW_FINISHED]


async def test_unavailable_updates_listeners(hass, coordinator):
    calls = []
    coordinator.async_add_listener(lambda: calls.append(coordinator.available))
    coordinator.available = True
    coordinator._on_unavailable(None)
    assert coordinator.available is False
    assert calls == [False]


def _step(coordinator, state):
    coordinator.state = state
    coordinator._track_brew()


async def test_ready_at_for_brew_started_from_ha(hass, coordinator):
    from homeassistant.util import dt as dt_util

    coordinator._brew_steep_seconds = 180
    coordinator._brew_started_at = dt_util.utcnow()
    _step(coordinator, IDLE)  # status read right after the start
    _step(coordinator, FILLING)
    assert coordinator.steeping_since is None
    _step(coordinator, STEEPING)
    assert coordinator.steeping_since is not None
    assert coordinator.ready_at == coordinator.steeping_since + timedelta(seconds=180)
    since = coordinator.steeping_since
    _step(coordinator, STEEPING)
    assert coordinator.steeping_since == since
    _step(coordinator, ENJOY)
    assert coordinator.steeping_since is None
    assert coordinator.ready_at is None
    assert coordinator._brew_steep_seconds is None


async def test_brew_started_on_machine_has_no_ready_at(hass, coordinator):
    _step(coordinator, STEEPING)
    assert coordinator.steeping_since is not None
    assert coordinator.ready_at is None


async def test_stale_ha_start_is_ignored(hass, coordinator):
    from homeassistant.util import dt as dt_util

    coordinator._brew_steep_seconds = 180
    coordinator._brew_started_at = dt_util.utcnow() - timedelta(minutes=30)
    _step(coordinator, STEEPING)
    assert coordinator.ready_at is None


class _Info:
    def __init__(self, mfr):
        self.manufacturer_data = mfr
        self.service_data = {}
        self.rssi = -60


async def test_raw_log_records_only_changes(hass, coordinator):
    for payload in (b"\x01\x04\x00", b"\x01\x04\x00", b"\x05\x1a\x00", b"\x05\x1a\x01"):
        coordinator._record_raw(_Info({0x1234: payload}))
    assert len(coordinator.raw_log) == 3
    assert coordinator.raw_log[-1]["manufacturer_data"] == {"4660": "051a01"}
    assert coordinator.raw_log[0]["delta_s"] is None
