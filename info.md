# BRU Maker One

Control a BRU Maker One tea machine from Home Assistant over Bluetooth.

## Install with HACS

The repository has to be public. In HACS open **Custom repositories**, add `https://github.com/saschaludwig/bru-ha-bt` as an **Integration**, then install **BRU Maker One** and restart Home Assistant.

[Add this repository to HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=saschaludwig&repository=bru-ha-bt&category=integration)

## Pairing

The machine ignores a new host until it shows **Waiting for connection** (Machine Setup, Pair New Device). Confirm the numeric pairing code on the Home Assistant host. After that bond, the same host reconnects without pairing mode. A phone that is already bonded is a different host.

State is read from Bluetooth advertisements. Starting or cancelling a brew opens a short connection, writes one command, and disconnects.

## Entities

- Status
- Temperature, steep time, and water amount
- Start brew and Cancel

Firmware updates are not part of this integration.
