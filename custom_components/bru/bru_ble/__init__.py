"""Bluetooth client for the BRU Maker One tea machine."""

from .advertisement import DiscoveredMachine, parse_advertisement
from .client import BruClient
from .commands import (
    build_brew_start,
    build_cancel,
    build_status_request,
    parse_notification,
)
from .errors import BrewRejected, BruError, MachineNotFound
from .status import MachineState

__all__ = [
    "BrewRejected",
    "BruClient",
    "BruError",
    "DiscoveredMachine",
    "MachineNotFound",
    "MachineState",
    "build_brew_start",
    "build_cancel",
    "build_status_request",
    "parse_advertisement",
    "parse_notification",
]
