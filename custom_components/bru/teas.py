"""Built-in tea profiles and parsing of user-defined ones."""

from __future__ import annotations

from dataclasses import dataclass

from .bru_ble.status import (
    nearest_steep_seconds,
    nearest_temperature_c,
    nearest_water_ml,
)

MANUAL = "manual"


@dataclass(frozen=True)
class Tea:
    """Brew settings for one tea. Water is optional: cup size is separate."""

    key: str
    temperature_c: int
    steep_seconds: int
    water_ml: int | None = None
    builtin: bool = True

    def snapped(self) -> Tea:
        return Tea(
            key=self.key,
            temperature_c=nearest_temperature_c(self.temperature_c),
            steep_seconds=nearest_steep_seconds(self.steep_seconds),
            water_ml=None if self.water_ml is None else nearest_water_ml(self.water_ml),
            builtin=self.builtin,
        )


# Common guidance, snapped to what the machine can brew.
BUILTIN_TEAS: tuple[Tea, ...] = (
    Tea("green", 80, 120),
    Tea("sencha", 70, 60),
    Tea("white", 80, 180),
    Tea("oolong", 90, 180),
    Tea("darjeeling", 85, 180),
    Tea("black", 95, 240),
    Tea("rooibos", 98, 360),
    Tea("herbal", 98, 480),
    Tea("fruit", 98, 600),
)


class TeaParseError(ValueError):
    """A line in the custom tea list could not be read."""


def parse_duration(text: str) -> int:
    """Read 180, 3:00, or 3m30s as seconds."""
    text = text.strip().lower().replace(" ", "")
    if not text:
        raise TeaParseError("empty steep time")
    if ":" in text:
        minutes, _, seconds = text.partition(":")
        return int(minutes or 0) * 60 + int(seconds or 0)
    if "m" in text or text.endswith("s"):
        minutes, _, rest = text.partition("m")
        if not rest and not text.endswith("m"):
            return int(text.rstrip("s"))
        return int(minutes or 0) * 60 + int(rest.rstrip("s") or 0)
    return int(text)


def parse_custom_teas(text: str) -> list[Tea]:
    """One tea per line: name; temperature; steep time[; water].

    Empty lines and lines starting with # are skipped.
    """
    teas: list[Tea] = []
    seen: set[str] = set()
    for number, raw in enumerate((text or "").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split(";")]
        if len(parts) not in (3, 4) or not parts[0]:
            raise TeaParseError(f"line {number}: expected name; °C; time[; ml]")
        name = parts[0]
        if name.lower() in seen or name == MANUAL:
            raise TeaParseError(f"line {number}: duplicate name {name}")
        try:
            temperature = int(float(parts[1].rstrip("°cC ")))
            seconds = parse_duration(parts[2])
            water = int(float(parts[3].rstrip("ml "))) if len(parts) == 4 and parts[3] else None
        except ValueError as err:
            raise TeaParseError(f"line {number}: {err}") from err
        seen.add(name.lower())
        teas.append(Tea(name, temperature, seconds, water, builtin=False).snapped())
    return teas


def all_teas(custom_text: str | None) -> dict[str, Tea]:
    """Built-in teas first, then custom ones (a custom name can shadow none)."""
    teas = {tea.key: tea.snapped() for tea in BUILTIN_TEAS}
    for tea in parse_custom_teas(custom_text or ""):
        if tea.key not in teas:
            teas[tea.key] = tea
    return teas
