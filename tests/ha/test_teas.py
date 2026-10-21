"""Tea select, number sync, options flow, and the bru.brew action."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.data_entry_flow import FlowResultType  # noqa: E402
from homeassistant.exceptions import ServiceValidationError  # noqa: E402
from homeassistant.helpers import device_registry as dr  # noqa: E402
from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: E402

from custom_components.bru.const import CONF_CUSTOM_TEAS, DOMAIN  # noqa: E402
from custom_components.bru.teas import (  # noqa: E402
    TeaParseError,
    parse_custom_teas,
    parse_duration,
)

ADDRESS = "AA:BB:CC:DD:EE:FF"
SELECT = "select.bru_tea"
TEMP = "number.bru_temperature"
STEEP = "number.bru_steep_time"
WATER = "number.bru_water"


def test_parse_custom_teas():
    teas = parse_custom_teas(
        "# mine\nEarl Grey; 95; 3:30\nMatcha; 81°C; 1m30s; 140 ml\n"
    )
    assert [(t.key, t.temperature_c, t.steep_seconds, t.water_ml) for t in teas] == [
        ("Earl Grey", 95, 210, None),
        ("Matcha", 80, 90, 150),  # snapped to machine steps
    ]
    assert parse_duration("4m") == 240
    with pytest.raises(TeaParseError):
        parse_custom_teas("only; two")
    with pytest.raises(TeaParseError):
        parse_custom_teas("A; 80; 60\na; 90; 60")


@pytest.fixture
async def loaded(hass: HomeAssistant):
    hass.config.components.add("bluetooth")  # skip real adapter setup
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"address": ADDRESS},
        options={CONF_CUSTOM_TEAS: "Earl Grey; 95; 3:30; 300"},
        title="BRU",
        unique_id=ADDRESS,
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.bru.coordinator.BruCoordinator.async_start",
            AsyncMock(),
        ),
        patch("custom_components.bru.coordinator.BruCoordinator.async_stop"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        yield entry


async def test_select_loads_tea_and_falls_back_to_manual(hass, loaded):
    state = hass.states.get(SELECT)
    assert state is not None
    assert "green" in state.attributes["options"]
    assert "Earl Grey" in state.attributes["options"]

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": SELECT, "option": "black"},
        blocking=True,
    )
    assert hass.states.get(SELECT).state == "black"
    assert float(hass.states.get(TEMP).state) == 95
    assert float(hass.states.get(STEEP).state) == 240

    await hass.services.async_call(
        "number", "set_value", {"entity_id": STEEP, "value": 300}, blocking=True
    )
    assert hass.states.get(SELECT).state == "manual"

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": SELECT, "option": "Earl Grey"},
        blocking=True,
    )
    assert float(hass.states.get(WATER).state) == 300
    assert hass.states.get(SELECT).attributes["steep_seconds"] == 210


async def test_brew_action(hass, loaded):
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, ADDRESS)})
    coordinator = loaded.runtime_data
    with patch.object(coordinator, "async_start_brew", AsyncMock()) as start:
        await hass.services.async_call(
            DOMAIN,
            "brew",
            {"device_id": device.id, "tea": "green", "steep_time": {"minutes": 3}},
            blocking=True,
        )
    start.assert_awaited_once()
    assert coordinator.temperature_c == 80
    assert coordinator.steep_seconds == 180  # override wins over the tea
    assert hass.states.get(SELECT).state == "manual"

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "brew", {"device_id": device.id, "tea": "nope"}, blocking=True
        )


async def test_options_flow_validates_and_reloads(hass, loaded):
    result = await hass.config_entries.options.async_init(loaded.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_CUSTOM_TEAS: "broken line"}
    )
    assert result["errors"] == {CONF_CUSTOM_TEAS: "invalid_teas"}
    with (
        patch(
            "custom_components.bru.coordinator.BruCoordinator.async_start", AsyncMock()
        ),
        patch("custom_components.bru.coordinator.BruCoordinator.async_stop"),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {CONF_CUSTOM_TEAS: "Chai; 98; 5:00"}
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "Chai" in hass.states.get(SELECT).attributes["options"]


async def test_status_sensor_is_a_translated_enum(hass, loaded):
    from custom_components.bru.bru_ble.status import MachineState

    coordinator = loaded.runtime_data
    coordinator.available = True
    coordinator.state = MachineState(status_code=5, sub_status_code=25)
    coordinator.async_notify()
    await hass.async_block_till_done()
    state = hass.states.get("sensor.bru_status")
    assert state.state == "filling"
    assert state.attributes["device_class"] == "enum"
    assert "steeping" in state.attributes["options"]
    assert state.attributes["sub_status"] == "brewingFillingUp"
