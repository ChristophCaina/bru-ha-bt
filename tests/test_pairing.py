"""Notify subscription pairs once when the link is not authenticated."""

import asyncio

import pytest
from bleak.exc import BleakError

from bru_ble.client import BruClient
from bru_ble.errors import PairingFailed

_AUTH = (
    "Bluetooth GATT Error address=FD:BF:FC:6B:3D:26 handle=16 "
    "error=5 description=Insufficient authentication"
)


class _Link:
    def __init__(self, *, stay_locked: bool = False) -> None:
        self.stay_locked = stay_locked
        self.paired = False
        self.notifies = 0
        self.pair_calls = 0
        self.is_connected = True

    async def connect(self) -> None:
        return None

    async def start_notify(self, _uuid, _callback) -> None:
        self.notifies += 1
        if self.stay_locked or not self.paired:
            raise BleakError(_AUTH)

    async def pair(self) -> None:
        self.pair_calls += 1
        self.paired = True

    async def read_gatt_char(self, _uuid) -> bytes:
        return b"290626-test"

    async def write_gatt_char(self, _uuid, _data, response: bool = True) -> None:
        return None

    async def disconnect(self) -> None:
        self.is_connected = False


def _install(monkeypatch, link: _Link) -> None:
    class _Client:
        def __new__(cls, _device):
            return link

    monkeypatch.setattr("bleak.BleakClient", _Client)


def test_pairs_on_the_connection_that_was_refused(monkeypatch):
    link = _Link()
    _install(monkeypatch, link)
    prompted = []
    asyncio.run(
        BruClient("FD:BF:FC:6B:3D:26", on_pairing=lambda: prompted.append(1)).connect()
    )
    assert link.pair_calls == 1
    assert link.notifies == 2
    assert prompted == [1]


def test_still_locked_after_pair_raises_pairing_failed(monkeypatch):
    link = _Link(stay_locked=True)
    _install(monkeypatch, link)
    with pytest.raises(PairingFailed):
        asyncio.run(BruClient("FD:BF:FC:6B:3D:26").connect())
    assert link.pair_calls == 1
