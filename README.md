# BRU Maker One

Bluetooth control for the [BRU Maker One](https://bru.shop) tea machine, recovered from the official Android app and reimplemented in Python.

The wire format is documented in [docs/protocol.md](docs/protocol.md).

## Home Assistant (HACS)

HACS only installs `custom_components/bru`. The Bluetooth library lives in that directory, so a normal HACS install is enough. Home Assistant 2025.1 or newer is required.

1. In HACS, open the three-dot menu and choose **Custom repositories**.
2. Add `https://github.com/saschaludwig/bru-ha-bt` with the category **Integration**.
3. Install **BRU Maker One** and restart Home Assistant.
4. Add the integration from Settings, Devices & services.

[Add this repository to HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=saschaludwig&repository=bru-ha-bt&category=integration)

Discovery uses the name `BRU` or the GATT service. After bonding, state comes from advertisements. Starting or cancelling a brew opens a short connection, writes one command, and disconnects.

Entities:

- Status sensor
- Temperature, steep time, and water amount
- Start brew and Cancel

Firmware updates and log transfer are not exposed.

To install without HACS, copy `custom_components/bru` into the Home Assistant config directory and restart.

## Pairing

Adding the device does not pair. The first **Start brew** opens the connection. The machine accepts a new controller only while it shows **Waiting for connection** (Machine Setup, Pair New Device). The six-digit code is confirmed on the controller that owns the link. A phone that is already bonded does not share its keys. Later commands from that same controller reconnect without pairing mode.

Home Assistant uses its own Bluetooth adapter when that adapter is the one in range. On Linux the BlueZ agent has to be running (`bluetoothctl`) so the code can be confirmed.

An ESPHome Bluetooth proxy becomes the controller when it is closer than the host. A stock proxy changes the connection parameters after service discovery and only starts pairing when Home Assistant asks, so the machine drops the link first. On the one proxy that should keep the bond, add:

```yaml
external_components:
  - source: github://saschaludwig/bru-ha-bt@main
    components: [bru_bond]

esp32_ble:
  io_capability: display_yes_no
  auth_req_mode: sc_mitm_bond

bru_bond:
  mac_address: "AA:BB:CC:DD:EE:FF"  # address shown for the machine
```

`bru_bond` starts encryption when the link opens and accepts the six-digit code itself. The bond is stored on that proxy. Other proxies in range need `bluetooth_proxy:` without `active: true`, or they take the connection and do not have the keys.

## Library

The same package can be installed on its own for scans and one-off commands:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

```bash
python -m bru_ble scan
python -m bru_ble status AA:BB:CC:DD:EE:FF
python -m bru_ble brew AA:BB:CC:DD:EE:FF --celsius 80 --seconds 180 --milliliters 250
python -m bru_ble cancel AA:BB:CC:DD:EE:FF
```

On Linux the BlueZ agent has to be running so it can display the pairing code (`bluetoothctl` with an agent).

## License

MIT. See [LICENSE](LICENSE).
