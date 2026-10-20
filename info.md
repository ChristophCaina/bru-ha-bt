# BRU Maker One

Control a BRU Maker One tea machine from Home Assistant over Bluetooth.

## Install with HACS

The repository has to be public. In HACS open **Custom repositories**, add `https://github.com/saschaludwig/bru-ha-bt` as an **Integration**, then install **BRU Maker One** and restart Home Assistant.

[Add this repository to HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=saschaludwig&repository=bru-ha-bt&category=integration)

## Pairing

Adding the device does not pair. The first **Start brew** opens the connection. The machine accepts a new controller only while it shows **Waiting for connection** (Machine Setup, Pair New Device). The six-digit code is confirmed on the controller that owns the link. A phone that is already bonded does not share its keys.

Home Assistant's own adapter can confirm the code when it is the adapter in range and a BlueZ agent is running. An ESPHome Bluetooth proxy cannot, until that proxy has a display and accepts numeric comparison. Allow the proxy to perform Home Assistant actions, then add:

```yaml
esp32_ble:
  io_capability: display_yes_no
  auth_req_mode: sc_mitm_bond

ble_client:
  - mac_address: "AA:BB:CC:DD:EE:FF"  # address shown for the machine
    id: bru_pairing
    auto_connect: false
    on_numeric_comparison_request:
      then:
        - homeassistant.action:
            action: persistent_notification.create
            data:
              notification_id: bru_pairing
              title: "BRU pairing"
              message: !lambda 'return "Code on the machine: " + str_sprintf("%06lu", (unsigned long) passkey);'
        - ble_client.numeric_comparison_reply:
            id: bru_pairing
            accept: true
```

The bond stays on that proxy. Set other nearby proxies to passive (`bluetooth_proxy:` without `active: true`).

State is read from Bluetooth advertisements. Starting or cancelling a brew opens a short connection, writes one command, and disconnects.

## Entities

- Status
- Temperature, steep time, and water amount
- Start brew and Cancel

Firmware updates are not part of this integration.
