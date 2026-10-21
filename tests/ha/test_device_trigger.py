"""Device triggers for brew lifecycle and machine prompts."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.components import automation  # noqa: E402
from homeassistant.components.device_automation import DeviceAutomationType  # noqa: E402
from homeassistant.helpers import device_registry as dr  # noqa: E402
from homeassistant.setup import async_setup_component  # noqa: E402
from pytest_homeassistant_custom_component.common import (  # noqa: E402
    MockConfigEntry,
    async_get_device_automations,
)

from custom_components.bru.bru_ble.status import MachineState  # noqa: E402
from custom_components.bru.const import DOMAIN  # noqa: E402

ADDRESS = "AA:BB:CC:DD:EE:FF"


@pytest.fixture
async def setup(hass):
    hass.config.components.add("bluetooth")
    entry = MockConfigEntry(
        domain=DOMAIN, data={"address": ADDRESS}, title="BRU", unique_id=ADDRESS
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.bru.coordinator.BruCoordinator.async_start", AsyncMock()
    ), patch("custom_components.bru.coordinator.BruCoordinator.async_stop"):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        device = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)[0]
        yield entry.runtime_data, device


async def test_lists_all_triggers(hass, setup):
    _, device = setup
    triggers = await async_get_device_automations(
        hass, DeviceAutomationType.TRIGGER, device.id
    )
    types = {t["type"] for t in triggers if t["domain"] == DOMAIN}
    assert types == {
        "brew_started",
        "brew_finished",
        "brew_cancelled",
        "add_water",
        "place_cup",
        "remove_cup",
        "close_lid",
        "error",
    }


async def _automation(hass, device_id, trigger_type):
    calls = []
    hass.services.async_register("test", "record", lambda call: calls.append(call.data))
    assert await async_setup_component(
        hass,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "triggers": {
                    "platform": "device",
                    "domain": DOMAIN,
                    "device_id": device_id,
                    "type": trigger_type,
                },
                "actions": {
                    "action": "test.record",
                    "data": {"what": "{{ trigger.event.data.type }}"},
                },
            }
        },
    )
    return calls


def _step(coordinator, status, sub):
    coordinator.state = MachineState(status_code=status, sub_status_code=sub, source="adv")
    coordinator._track_brew()


async def test_brew_finished_trigger(hass, setup):
    coordinator, device = setup
    calls = await _automation(hass, device.id, "brew_finished")
    _step(coordinator, 5, 26)  # steeping
    _step(coordinator, 5, 30)  # ready to enjoy
    await hass.async_block_till_done()
    assert [c["what"] for c in calls] == ["brew_finished"]


async def test_add_water_prompt_fires_once(hass, setup):
    coordinator, device = setup
    calls = await _automation(hass, device.id, "add_water")
    _step(coordinator, 1, 4)
    _step(coordinator, 11, 124)  # msgAddWater
    _step(coordinator, 11, 124)  # repeated advert, no second trigger
    _step(coordinator, 1, 4)
    await hass.async_block_till_done()
    assert [c["what"] for c in calls] == ["add_water"]


async def test_other_device_does_not_trigger(hass, setup):
    coordinator, _ = setup
    calls = await _automation(hass, "someone-else", "add_water")
    _step(coordinator, 11, 124)
    await hass.async_block_till_done()
    assert calls == []


async def test_prompt_binary_sensors(hass, setup):
    coordinator, _ = setup
    coordinator.available = True
    _step(coordinator, 11, 124)  # msgAddWater
    coordinator.async_notify()
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.bru_add_water").state == "on"
    assert hass.states.get("binary_sensor.bru_cup_missing").state == "off"
    assert hass.states.get("binary_sensor.bru_close_lid").state == "off"
    assert (
        hass.states.get("binary_sensor.bru_close_lid").attributes["device_class"]
        == "problem"
    )
    _step(coordinator, 1, 4)
    coordinator.async_notify()
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.bru_add_water").state == "off"
