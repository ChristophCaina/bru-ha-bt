# BRU Maker One

Control a BRU Maker One tea machine from Home Assistant over Bluetooth.

## Install with HACS

In HACS open **Custom repositories**, add `https://github.com/saschaludwig/bru-ha-bt` as an **Integration**, then install **BRU Maker One** and restart Home Assistant.

[Add this repository to HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=saschaludwig&repository=bru-ha-bt&category=integration)

## Pairing

Adding the device does not pair. The first **Start brew** opens the connection. The machine accepts a new controller only while it shows **Waiting for connection** (Machine Setup, Pair New Device). The six-digit code is confirmed on the controller that owns the link. A phone that is already bonded does not share its keys.

Home Assistant's own adapter can confirm the code when it is the adapter in range and a BlueZ agent is running. On the ESPHome proxy that should keep the bond, add:

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

The proxy accepts the code itself. The bond stays on that proxy. Set other nearby proxies to passive (`bluetooth_proxy:` without `active: true`).

State is read from Bluetooth advertisements. Starting or cancelling a brew opens a short connection, writes one command, and disconnects.

## Entities

- Status
- Temperature, steep time, and water amount
- Start brew and Cancel

Firmware updates are not part of this integration.
