"""Errors raised while talking to a BRU machine."""


class BruError(Exception):
    """Base error for the BRU client."""


class BrewRejected(BruError):
    """The machine refused a brew command."""

    def __init__(self, code: int, label: str) -> None:
        self.code = code
        self.label = label
        super().__init__(f"Brew rejected ({code}): {label}")


class MachineNotFound(BruError):
    """No bonded or advertising BRU machine matched the request."""


class ResponseTimeout(BruError):
    """The machine did not answer a command in time."""
