# Narwal T10 — Home Assistant integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A custom [Home Assistant](https://www.home-assistant.io/) integration for the **Narwal T10**
robot vacuum. It talks to Narwal's cloud, which is the only control path the T10 exposes, and
was fully reverse-engineered from the official app and verified live. Existing community
integrations target newer models' local protocols and do not work on the T10.

## Features

- **Vacuum entity**: start, pause, stop, return to dock, and fan speed.
- **Live status**: battery, docked/charging, fan level, cleaned area, and error.
- **Cloud login** with your Narwal email and password; no tokens to extract.

## Supported devices

- **Narwal T10** (firmware v4.x), via the `usawebsocket.narwaltech.com` cloud.

Other older Narwal models that use the same `/app_websocket` cloud path may work. The newer
Freo / X-series models use a different protocol and are covered by other integrations.

## Installation

### HACS (custom repository)

1. HACS → three-dot menu → **Custom repositories**.
2. Add `https://github.com/nitinkr0411/ha-narwal-t10`, category **Integration**.
3. Find **Narwal T10 (cloud)** in HACS and download it.
4. **Restart Home Assistant.**
5. Settings → Devices & Services → **Add Integration** → **Narwal T10**.
6. Enter your Narwal app email, password, and region.

### Manual

Copy `custom_components/narwal_t10/` into your Home Assistant `config/custom_components/`,
restart, and add the integration from the UI.

## How it works

The T10's cloud uses AES-128-ECB-encrypted JSON over a WebSocket. This integration logs in
over REST, discovers the robot's `machine_id`, builds the `APP-AUTH` handshake, connects to
`wss://usawebsocket.narwaltech.com/app_websocket`, and exchanges
`base64(AES-128-ECB(json))` frames. The status path is verified byte-for-byte against the app.

## Status

- **Status (battery, dock, fan, area, error): verified live.**
- **Commands (start/pause/stop/dock/fan): the services are verified, the exact command verbs
  are inferred from the app and may need a one-line tweak in `const.py` if a command has no
  effect.** See the component README for details.
- An idle, docked robot disconnects from the cloud; status then returns nothing until it
  wakes. That is expected.

## Disclaimer

Unofficial. Not affiliated with, endorsed by, or supported by Narwal. The cloud protocol was
reverse-engineered from the official app for interoperability. Use at your own risk.
