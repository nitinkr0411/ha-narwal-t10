# Narwal T10 — Home Assistant integration (cloud)

Controls a Narwal **T10** robot vacuum through Narwal's cloud. The T10's protocol
was fully reverse-engineered and verified against a live account and the official
app's traffic; existing community integrations only support newer models' local
protocols and do not work on the T10.

**v1 scope:** live status (battery, docked/charging, fan level, cleaned area, error)
plus start / pause / stop / return-to-dock / fan speed.

## How it works (verified protocol)

1. **REST login** — `POST https://usaclient.narwaltech.com/user/email/login/pw/`
   with email + password returns a JWT. Sent on later calls as the `auth-token` header.
2. **Device discovery** — `GET /robot/` returns the robot's `machine_id`, `robot_id`,
   name, model, and firmware.
3. **Cloud WebSocket** — `wss://usawebsocket.narwaltech.com/app_websocket`, authenticated
   by an `APP-AUTH` header. Both the header and every frame are
   **`base64( AES-128-ECB( JSON ) )`** with a key extracted from the app.
   - APP-AUTH plaintext: `{"machine_id","token","version":"Av2"}`
   - Frame plaintext: `{"request_id","machine_id","service","params"}` → response
     `{"code","request_id","result":{...}}`
4. **Status** — service `/pita/info/all` returns `battery_per`, `charge_status`,
   `station_contact` (on dock), `work_status`, `mode_strength` (fan), `cleaned_area`,
   `error_code`, and more.

This is all implemented in `narwal_client/` and verified end-to-end against the live
robot (status pull returns real data; a valid APP-AUTH keeps the socket open).

## Status / caveats

- **Status path: fully verified** against the live robot.
- **Commands (start/pause/stop/dock/fan): the service is verified
  (`/pita_clean_system/command`, `/pita/config/set_sweep_strength`), but the exact
  param verbs (`Start_Clean`, etc. in `const.py`) are inferred from app strings and
  were not captured live.** Confirm them by capturing one command from the app (see
  below) if a command doesn't take effect, and adjust `const.py`.
- The robot disconnects from the cloud when idle for a while; a status pull then
  returns nothing until it wakes. That's normal, not a bug.

## Install

1. `pip install pycryptodome` is handled by the manifest `requirements`.
2. Copy `custom_components/narwal_t10/` into Home Assistant `config/custom_components/`.
3. Restart Home Assistant.
4. Settings → Devices & Services → Add Integration → **Narwal T10**.
5. Enter your Narwal email, password, and region.

## CLI (validation)

From inside `custom_components/narwal_t10/`, with `aiohttp` + `pycryptodome`:

```bash
export NARWAL_EMAIL=you@example.com NARWAL_PASSWORD='...'
python -m narwal_client.cli --region us robots      # list robots
python -m narwal_client.cli --region us status      # live status snapshot
python -m narwal_client.cli --region us fan strong  # set fan speed
python -m narwal_client.cli --region us raw /pita/info/all   # any service
```

## Tests

```bash
pip install aiohttp pycryptodome pytest && pytest tests/
```

Includes a known-answer vector proving `APP-AUTH` generation is byte-identical to the
app, and decoding a real captured status frame.

## Attribution

Protocol reverse-engineered from the official T10 app and live traffic. The AES key and
frame format are the app's. Not affiliated with or endorsed by Narwal.
