# BRU Maker One BLE protocol

Facts recovered from the BRU Android app (`shop.bru.bruapp.apk`). The app is React Native. Bluetooth I/O is `react-native-ble-plx` (`com.polidea.rxandroidble2`). The command framing lives in the Hermes bytecode bundle `assets/index.android.bundle` (bytecode version 96), in `getCommand`, `_calcChecksum`, and the `commands` table.

This note describes the wire format that `bru_ble` reimplements. It is not a copy of the app.

## GATT

| Role | UUID |
| --- | --- |
| Service | `aae28f00-71b5-42a1-8c3c-f9cf6ac969d0` |
| Notify | `aae28f01-71b5-42a1-8c3c-f9cf6ac969d0` |
| Write | `aae28f02-71b5-42a1-8c3c-f9cf6ac969d0` |

Firmware version is the standard Device Information characteristic `00002a26-0000-1000-8000-00805f9b34fb` on service `0000180a-0000-1000-8000-00805f9b34fb`.

The app scans for a local name containing `BRU` (`looksLikeBruMachine`) and also reads manufacturer data or service data for `aae28f00-…`. A separate DFU scan looks for `dfu`, `targ`, or `bru_u`. Firmware update is out of scope.

## Pairing

The machine must be in **Machine Setup → Pair New Device** until the display says `Waiting for connection`. The link is LE Secure Connections with numeric comparison: the code on the machine has to be confirmed on the controller that owns the connection. A controller with no display and no yes/no is rejected. After bonding, the app writes `setTime` as its first encrypted operation. A rejection of that write before any encrypted operation succeeds means the code was declined. Later reconnects reuse the bond. The machine is effectively invisible to adapters that are not bonded and that are not in pairing mode.

The app connects only for a command (`TransientBrew`: connect, write, disconnect) and otherwise tracks state from advertisements.

## Frame

Every command and every notification uses the same frame:

```
FF  <length>  <opcode>  <payload…>  <checksum>
```

`length` is the total frame size, including the checksum. The payload is padded with `0x00` so that the byte count before the checksum is `length - 1`.

The checksum is the unsigned 8-bit value of `(-sum(bytes_before_checksum)) XOR 0x3A`.

Examples:

| Command | Frame |
| --- | --- |
| Status (`0x44`) | `ff044483` |
| Cancel brew (`0x42`) | `ff044281` |
| Brew 80 °C, 180 s, 250 ml | `ff0f400008110400000001000000ae` |

## Opcodes

Request opcodes from the app `commands` object, plus the cancel opcode used by `cancelProcess`:

| Name | Opcode | Response |
| --- | --- | --- |
| Set time | `0x08` | |
| Get machine setup | `0x2A` | |
| Set machine setup | `0x2C` | |
| Start brew | `0x40` | `0x41` brew result |
| Cancel brew | `0x42` | |
| Status | `0x44` | `0x45` status payload |
| Button press | `0x46` | `0x47` button result |
| Get preset by id (1–10) | `0x50` | |
| Update preset | `0x52` | |
| Update nickname | `0x4A` | |
| Next log record | `0x54` | `0x55` / `0x56` |
| Confirm log transfer | `0x57` | |
| Log debug read | `0x59` | |
| Debug / flash clear | `0x5B` | |

Log transfer and flash clear (`0x5B` with debug subcommand `1`) erase or upload machine logs. They are not part of the control library.

### Status request

`FF 04 44 <checksum>`. The `0x45` notification carries the main status at byte 3 and the sub-status at byte 4.

### Start brew (`0x40`)

Legacy payload, 11 bytes, frame length 15:

| Offset | Meaning |
| --- | --- |
| 0 | Reserved `0` |
| 1 | Temperature byte |
| 2 | Time byte |
| 3 | Water byte |
| 4 | Rinse: `0` off, `1` cup, `2` tray |
| 5 | Rinse intensity: `0` short, `1` normal, `2` intense |
| 6 | Rinse delay in seconds (`0` = off) |
| 7 | Buzzer: `1` on, `0` off |
| 8–10 | Reserved `0` |

The instant-brew path sends rinse off, intensity `0`, delay `0`, buzzer on.

Firmware whose datestamp is at least `290626` (the text before `-` in the DIS version, compared as a date) also accepts an extended payload: the 11 bytes above followed by an 8-byte app id, a 48-byte UTF-16LE name (24 characters, the app trims to 12), and a little-endian tea id. `bru_ble` sends the legacy payload unless an identity is supplied. The `0x41` response stores the result code at byte 3.

| Result | Meaning |
| --- | --- |
| `0` | Accepted |
| `1` | Command format rejected |
| `3` | Temperature not supported |
| `4` | Time not supported |
| `5` | Water amount not supported (25 ml steps need a newer firmware) |
| `16` | Machine not ready (lid, tank, or cup) |

### Temperature byte

| Byte | °C |
| --- | --- |
| 0 | Cold (reported as 0) |
| 1–11 | 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95 |
| 12 | 98 (maximum) |

### Time byte

The picker starts at 10 seconds. For hours 0–9 it emits `H:00` (skipped at hour 0) and then `H:10` … `H:50`. Hours 10–60 emit the full hour only. The byte is the index in that list. 10 s is byte `0`, 180 s is byte `17`, 600 s is byte `59`.

### Water byte

| ml | Byte |
| --- | --- |
| 50, 100, 150, 200, 250, 300, 350 | 0–6 |
| 75, 125, 175, 225, 275, 325 | 128–133 |

The 25 ml steps are gated in the app by firmware datestamp `280526`. Older firmware answers the brew with result `5`.

### Set time (`0x08`)

Frame length 8. Payload is the Unix time as a little-endian `uint32` (4 bytes). The app derives it from `Date.getTime() / 1000` after its date helper.

### Button (`0x46`)

Frame length 5. Payload is one button id byte.

### Preset read (`0x50`)

Frame length 5. Payload is the preset id, 1 through 10.

### Preset write (`0x52`)

Frame length 56, or 60 when a tea id is included.

```
preset_id, time_byte, temperature_byte, water_byte, name[48]
```

`name` is UTF-16LE, 24 code units, zero padded. The app trims the visible name to 12 characters. A numeric tea id adds 4 little-endian bytes and raises the length to 60.

### Nickname (`0x4A`)

Same 48-byte UTF-16LE name, frame length 56, trimmed to 12 characters.

### Machine setup (`0x2C`)

Frame length 8: `language, units, time_format, preset_count`.

## Advertisements

`parseAdvertisingData` base64-decodes manufacturer data, or service data for `aae28f00-…` when manufacturer data is absent. Byte 3 is the main status and byte 4 is the sub-status, using the same enums as a `0x45` notification.

On Bleak, manufacturer data is split: the company id is the dictionary key and the value starts at byte 2 of the buffer the app sees. Reconstruct `company_id.to_bytes(2, "little") + value` before indexing. Service data is already the raw value.

A connected status overrides the advertised status (`getEffectiveStatus`).

### Main status (`bruStatusEnum`)

`1` StandbyMode, `2` FunctionMenu, `3` MachineSetup, `4` MachineSetupHidden, `5` Brewing, `6` Dispensing, `7` AlarmTimer, `8` ColdTea, `9` SplitCup, `10` MultiSteeping, `11` InfoMessge, `12` WarningMessage, `13` ErrorMessage, `14` HotTea, `15` ManufTest, `16` ManualTest, `17` DurabPVtest, `18` DurabPumptest, `19` DurabHeatertest, `20` DurabFulltest, `21` Drying, `22` Descaling, `23` LidReminder, `24` BluetoothMenu.

### Sub-status

Byte value to name, from `bruSubStatusEnum`. Gaps in the numbering are unused.

`0` null, `1` languageChoice, `2` homeScreensaver, `3` introScreen, `4` homeScreen, `5` editBrewingTime, `6` editTemperature, `7` editWaterAmount, `10` presetStatus, `11` multiSteeping, `12` multiSteepingEdit, `13` dispenserStatus, `14` timerScreen, `15` timerRunning, `16` coldTeaScreen, `17` coldTeaEdit, `18` splitCupScreen, `19` hotTeaScreen, `20` hotTeaEdit, `21` hotTea2Screen, `22` hotTea2Edit, `25` brewingFillingUp, `26` brewingSteeping, `27` brewingRinseDelay, `28` brewingServing, `29` brewingRinse, `30` brewingEnjoy, `31` brewingColdWater, `32` brewingHotWater, `33` dispensing, `40`–`81` setup screens, `90`–`108` descaling steps, `110`–`113` Bluetooth setup, `120`–`132` prompts (place cup, add water, close lid, error, …), `140`–`157` hardware setup, `160`–`166` test and drying, `227`–`234` info, water filter, and firmware update.

Brewing progress that matters for automations is `brewingFillingUp`, `brewingHotWater`, `brewingSteeping`, `brewingServing`, `brewingRinse`, and `brewingEnjoy`.
