"""Encode and decode tests for the BRU frame format."""

from bru_ble.advertisement import parse_advertisement
from bru_ble.commands import (
    build_brew_identity,
    build_brew_start,
    build_cancel,
    build_get_preset,
    build_machine_setup,
    build_nickname,
    build_set_time,
    build_status_request,
    build_update_preset,
    checksum,
    firmware_wants_extended_brew,
    parse_notification,
)
from bru_ble.status import (
    temperature_byte,
    time_byte,
    water_byte,
)


def test_checksum_matches_the_app_formula():
    body = bytes.fromhex("ff0444")
    assert checksum(body) == 0x83


def test_status_and_cancel_frames():
    assert build_status_request().hex() == "ff044483"
    assert build_cancel().hex() == "ff044281"


def test_brew_frame_for_a_typical_cup():
    frame = build_brew_start(80, 180, 250)
    assert frame.hex() == "ff0f400008110400000001000000ae"
    assert temperature_byte(80) == 8
    assert time_byte(180) == 17
    assert water_byte(250) == 4


def test_extended_brew_frame_follows_the_datestamp():
    assert firmware_wants_extended_brew("290626-1")
    assert firmware_wants_extended_brew("010726-1")
    assert not firmware_wants_extended_brew("280626-1")
    assert not firmware_wants_extended_brew(None)
    assert not firmware_wants_extended_brew("abc")

    identity = build_brew_identity()
    assert len(identity) == 8 + 48 + 4
    frame = build_brew_start(80, 180, 250, identity=identity)
    assert len(frame) == 75
    assert frame[2] == 0x40
    assert frame[3:14] == bytes.fromhex("0008110400000001000000")
    assert frame[-1] == checksum(frame[:-1])


def test_temperature_and_water_snap_to_supported_steps():
    assert temperature_byte(82) == temperature_byte(80)
    assert temperature_byte(98) == 12
    assert temperature_byte(0) == 0
    assert water_byte(75) == 128
    assert water_byte(240) == water_byte(250)


def test_time_byte_known_points():
    assert time_byte(10) == 0
    assert time_byte(180) == 17
    assert time_byte(600) == 59


def test_set_time_is_little_endian_unix():
    frame = build_set_time(0x01020304)
    assert frame[0:3] == bytes((0xFF, 8, 0x08))
    assert frame[3:7] == bytes((0x04, 0x03, 0x02, 0x01))
    assert frame[-1] == checksum(frame[:-1])
    assert len(frame) == 8


def test_preset_and_setup_lengths():
    assert len(build_get_preset(3)) == 5
    assert build_get_preset(3)[2] == 0x50
    updated = build_update_preset(2, 80, 180, 250, "Sencha")
    assert len(updated) == 56
    assert updated[2] == 0x52
    with_tea = build_update_preset(2, 80, 180, 250, "Sencha", tea_id=0x11223344)
    assert len(with_tea) == 60
    assert with_tea[-5:-1] == bytes((0x44, 0x33, 0x22, 0x11))
    nick = build_nickname("Kitchen")
    assert len(nick) == 56
    assert nick[2] == 0x4A
    setup = build_machine_setup(1, 0, 1, 4)
    assert len(setup) == 8
    assert setup[2] == 0x2C


def test_status_notification_and_brew_result():
    status = bytes((0xFF, 6, 0x45, 5, 26))
    status += bytes((checksum(status),))
    parsed = parse_notification(status)
    assert parsed is not None
    assert parsed.checksum_ok
    assert parsed.state is not None
    assert parsed.state.status == "Brewing"
    assert parsed.state.sub_status == "brewingSteeping"
    assert parsed.state.label == "Steeping"

    result = bytes((0xFF, 5, 0x41, 0))
    result += bytes((checksum(result),))
    parsed = parse_notification(result)
    assert parsed is not None
    assert parsed.brew_result is not None
    assert parsed.brew_result.success
    assert parsed.brew_result.code == 0


def test_advertisement_uses_bytes_three_and_four():
    raw = bytes((0x34, 0x12, 0x00, 5, 26))
    company = int.from_bytes(raw[:2], "little")
    found = parse_advertisement(
        "AA:BB:CC:DD:EE:FF",
        "BRU Maker",
        manufacturer_data={company: raw[2:]},
    )
    assert found is not None
    assert found.state is not None
    assert found.state.label == "Steeping"


def test_ignores_unrelated_devices_and_dfu_adverts():
    assert parse_advertisement("AA:BB:CC:DD:EE:FF", "Headphones") is None
    assert parse_advertisement("AA:BB:CC:DD:EE:FF", "dfu-target") is None
