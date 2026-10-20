"""Status enums and the brew parameter encoding used by the machine."""

from __future__ import annotations

from dataclasses import dataclass

# Main status byte -> name. The app spells InfoMessge that way.
STATUS_NAMES: dict[int, str] = {
    1: "StandbyMode",
    2: "FunctionMenu",
    3: "MachineSetup",
    4: "MachineSetupHidden",
    5: "Brewing",
    6: "Dispensing",
    7: "AlarmTimer",
    8: "ColdTea",
    9: "SplitCup",
    10: "MultiSteeping",
    11: "InfoMessge",
    12: "WarningMessage",
    13: "ErrorMessage",
    14: "HotTea",
    15: "ManufTest",
    16: "ManualTest",
    17: "DurabPVtest",
    18: "DurabPumptest",
    19: "DurabHeatertest",
    20: "DurabFulltest",
    21: "Drying",
    22: "Descaling",
    23: "LidReminder",
    24: "BluetoothMenu",
}

SUBSTATUS_NAMES: dict[int, str] = {
    0: "null",
    1: "languageChoice",
    2: "homeScreensaver",
    3: "introScreen",
    4: "homeScreen",
    5: "editBrewingTime",
    6: "editTemperature",
    7: "editWaterAmount",
    10: "presetStatus",
    11: "multiSteeping",
    12: "multiSteepingEdit",
    13: "dispenserStatus",
    14: "timerScreen",
    15: "timerRunning",
    16: "coldTeaScreen",
    17: "coldTeaEdit",
    18: "splitCupScreen",
    19: "hotTeaScreen",
    20: "hotTeaEdit",
    21: "hotTea2Screen",
    22: "hotTea2Edit",
    25: "brewingFillingUp",
    26: "brewingSteeping",
    27: "brewingRinseDelay",
    28: "brewingServing",
    29: "brewingRinse",
    30: "brewingEnjoy",
    31: "brewingColdWater",
    32: "brewingHotWater",
    33: "dispensing",
    40: "setupScreen",
    41: "setupCurrentTime",
    42: "setupTimeHours",
    43: "setupTimeMinutes",
    44: "setupTimeAmPm",
    45: "setupRinse",
    46: "setupRinseEdit",
    47: "setupRinseIntensity",
    48: "setupRinseIntensityEdit",
    49: "setupRinseWaitTime",
    50: "setupRinseWaitTimeEdit",
    51: "setupMultiSteeping",
    52: "setupMultiSteepingEdit",
    53: "setupDispenser",
    54: "setupDispenserEdit",
    55: "setupAlarm",
    56: "setupAlarmEdit",
    57: "setupAlarmHours",
    58: "setupAlarmMinutes",
    59: "setupAlarmAmPm",
    60: "setupCooldown",
    61: "setupCooldownEdit",
    62: "setupSplitCup",
    63: "setupSplitCupEdit",
    64: "setupHotTea",
    65: "setupHotTeaEdit",
    66: "setupScreensaver",
    67: "setupScreensaverEdit",
    68: "setupRgb",
    69: "setupRgbEdit",
    70: "setupBuzzer",
    71: "setupBuzzerEdit",
    72: "setupLanguage",
    73: "setupLanguageEdit",
    74: "setupUnits",
    75: "setupUnitsEdit",
    76: "setupTimeFormat",
    77: "setupTimeFormatEdit",
    78: "setupLidReminder",
    79: "setupLidReminderEdit",
    80: "setupHotTea2",
    81: "setupHotTea2Edit",
    90: "descalingIntro",
    91: "descalingStatus",
    92: "descalingRinsePumpOn",
    93: "descaleWithAdapter",
    94: "descaleAdapterInst",
    95: "descaleInCup",
    96: "descaleScanQr",
    97: "descaleInstallAdapter",
    98: "descaleAddDescaler",
    99: "descalingEnd",
    100: "descalingRinseSystem",
    101: "descalingCheckWater",
    102: "descalingRefillWater",
    103: "descalingCheckLid",
    104: "descalingPila",
    105: "descalingRinseEnd",
    106: "setupPresetAmount",
    107: "setupPresetAmountEdit",
    108: "descalingRinsePumpOff",
    110: "setupBle",
    111: "setupBleEdit",
    112: "setupBlePairing",
    113: "setupBlePairingEdit",
    120: "msgPlaceCup",
    121: "msgRemoveCup",
    122: "msgCloseLid",
    123: "msgOpenLid",
    124: "msgAddWater",
    125: "msgInsertChamber",
    126: "msgNoNozzle",
    127: "msgError",
    128: "msgContinue",
    129: "msgCancel",
    130: "msgNextCup",
    131: "msgCupRemoved",
    132: "msgPlaceDescaling",
    133: "checkEngineInfo",
    140: "setupChamber",
    141: "setupChamberEdit",
    142: "setupNozzle",
    143: "setupNozzleEdit",
    144: "setupLid",
    145: "setupLidEdit",
    146: "setupCup",
    147: "setupCupEdit",
    148: "setupIrCalibration",
    149: "setupIrCalibrationExe",
    150: "setupOpenPls",
    151: "setupOpenPlsEdit",
    152: "setupClosePls",
    153: "setupClosePlsEdit",
    154: "setupDescaling",
    155: "setupDescalingEdit",
    156: "setupFactoryReset",
    157: "setupFactoryResetEdit",
    160: "debugMenuEnter",
    161: "manufTestsEnter",
    162: "manufTests",
    163: "manufTestsEdit",
    164: "manualTestsEnter",
    165: "durabilityTestsEnter",
    166: "dryingMachine",
    227: "infoPvClosing",
    228: "infoPvOpening",
    229: "waterFilter",
    230: "waterFilterEdit",
    231: "waterFilterReset",
    232: "waterFilterResetExe",
    233: "firmwareUpdate",
    234: "functionInDevelopment",
}

# Short labels for the states a Home Assistant user actually sees.
FRIENDLY_SUBSTATUS: dict[str, str] = {
    "homeScreen": "Ready",
    "homeScreensaver": "Idle",
    "brewingFillingUp": "Filling",
    "brewingHotWater": "Heating",
    "brewingColdWater": "Adding cold water",
    "brewingSteeping": "Steeping",
    "brewingRinseDelay": "Rinse delay",
    "brewingServing": "Serving",
    "brewingRinse": "Rinsing",
    "brewingEnjoy": "Ready to enjoy",
    "dispensing": "Dispensing",
    "msgPlaceCup": "Place a cup",
    "msgRemoveCup": "Remove the cup",
    "msgCloseLid": "Close the lid",
    "msgOpenLid": "Open the lid",
    "msgAddWater": "Add water",
    "msgInsertChamber": "Insert the chamber",
    "msgNoNozzle": "Nozzle not detected",
    "msgError": "Error",
    "msgPlaceDescaling": "Place the descaling adapter",
}

TEMPERATURE_C_TO_BYTE: dict[int, int] = {
    0: 0,
    45: 1,
    50: 2,
    55: 3,
    60: 4,
    65: 5,
    70: 6,
    75: 7,
    80: 8,
    85: 9,
    90: 10,
    95: 11,
    98: 12,
}
BYTE_TO_TEMPERATURE_C: dict[int, int] = {
    byte: celsius for celsius, byte in TEMPERATURE_C_TO_BYTE.items()
}

WATER_ML_TO_BYTE: dict[int, int] = {
    50: 0,
    100: 1,
    150: 2,
    200: 3,
    250: 4,
    300: 5,
    350: 6,
    75: 128,
    125: 129,
    175: 130,
    225: 131,
    275: 132,
    325: 133,
}
BYTE_TO_WATER_ML: dict[int, int] = {
    byte: milliliters for milliliters, byte in WATER_ML_TO_BYTE.items()
}

RINSE_NAMES = {0: "off", 1: "cup", 2: "tray"}
RINSE_INTENSITY_NAMES = {0: "short", 1: "normal", 2: "intense"}

BREW_RESULT_LABELS = {
    0: "success",
    1: "rejected_format",
    3: "invalid_temperature",
    4: "invalid_time",
    5: "invalid_water_amount",
    16: "machine_not_ready",
}

BUSY_SUBSTATUSES = {
    "brewingFillingUp",
    "brewingHotWater",
    "brewingColdWater",
    "brewingSteeping",
    "brewingRinseDelay",
    "brewingServing",
    "brewingRinse",
    "dispensing",
}


def _build_time_table() -> dict[int, int]:
    """Map steep seconds to the picker byte used on the wire."""
    table: dict[int, int] = {}
    value = 0
    for hour in range(10):
        if hour:
            table[hour * 60] = value
            value += 1
        for tenth in range(1, 6):
            table[hour * 60 + tenth * 10] = value
            value += 1
    for hour in range(10, 61):
        table[hour * 60] = value
        value += 1
    return table


SECONDS_TO_TIME_BYTE = _build_time_table()
TIME_BYTE_TO_SECONDS = {
    byte: seconds for seconds, byte in SECONDS_TO_TIME_BYTE.items()
}


def nearest_temperature_c(celsius: float) -> int:
    """Snap a requested temperature to a value the machine can brew."""
    return min(
        TEMPERATURE_C_TO_BYTE,
        key=lambda choice: (abs(choice - celsius), choice),
    )


def temperature_byte(celsius: float) -> int:
    """Encode a temperature as the brew payload byte."""
    return TEMPERATURE_C_TO_BYTE[nearest_temperature_c(celsius)]


def nearest_water_ml(milliliters: float) -> int:
    """Snap a requested volume to a supported water byte."""
    return min(
        WATER_ML_TO_BYTE,
        key=lambda choice: (abs(choice - milliliters), choice),
    )


def water_byte(milliliters: float) -> int:
    """Encode a water volume as the brew payload byte."""
    return WATER_ML_TO_BYTE[nearest_water_ml(milliliters)]


def nearest_steep_seconds(seconds: float) -> int:
    """Snap a requested steep time to a value the picker can encode."""
    return min(
        SECONDS_TO_TIME_BYTE,
        key=lambda choice: (abs(choice - seconds), choice),
    )


def time_byte(seconds: int) -> int:
    """Encode a steep time. The machine steps in 10 second increments."""
    return SECONDS_TO_TIME_BYTE[nearest_steep_seconds(seconds)]


def friendly_state(status: str | None, sub_status: str | None) -> str:
    """One line a sensor can show."""
    if sub_status and sub_status in FRIENDLY_SUBSTATUS:
        return FRIENDLY_SUBSTATUS[sub_status]
    if sub_status and sub_status != "null":
        return sub_status
    if status:
        return status
    return "Unknown"


@dataclass(frozen=True)
class MachineState:
    """Decoded machine state from an advertisement or a status notification."""

    status_code: int | None = None
    sub_status_code: int | None = None
    source: str = "none"

    @property
    def status(self) -> str | None:
        if self.status_code is None:
            return None
        return STATUS_NAMES.get(self.status_code, f"unknown_{self.status_code}")

    @property
    def sub_status(self) -> str | None:
        if self.sub_status_code is None:
            return None
        return SUBSTATUS_NAMES.get(
            self.sub_status_code, f"unknown_{self.sub_status_code}"
        )

    @property
    def label(self) -> str:
        return friendly_state(self.status, self.sub_status)

    @property
    def busy(self) -> bool:
        return self.sub_status in BUSY_SUBSTATUSES or self.status in {
            "Brewing",
            "Dispensing",
            "Descaling",
        }


@dataclass(frozen=True)
class BrewResult:
    """Result byte from a 0x41 brew response."""

    code: int

    @property
    def success(self) -> bool:
        return self.code == 0

    @property
    def label(self) -> str:
        return BREW_RESULT_LABELS.get(self.code, f"unknown_{self.code}")
