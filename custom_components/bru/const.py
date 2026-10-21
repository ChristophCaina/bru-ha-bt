"""Constants for the BRU Maker One integration."""

DOMAIN = "bru"

CONF_ADDRESS = "address"

DEFAULT_TEMPERATURE_C = 80
DEFAULT_STEEP_SECONDS = 180
DEFAULT_WATER_ML = 250

EVENT_BREW = "bru_brew"
BREW_STARTED = "brew_started"
BREW_FINISHED = "brew_finished"
BREW_CANCELLED = "brew_cancelled"
BREW_EVENT_TYPES = [BREW_STARTED, BREW_FINISHED, BREW_CANCELLED]

CONF_CUSTOM_TEAS = "custom_teas"
SERVICE_BREW = "brew"
