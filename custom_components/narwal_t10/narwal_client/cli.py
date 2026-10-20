"""CLI to exercise the Narwal T10 cloud protocol against a real account.

    python -m narwal_client.cli --email you@example.com --password ... <command>

Commands:
    robots                 log in and list bound robots
    status                 connect the WebSocket and print one status snapshot
    watch                  connect and print status updates until Ctrl-C
    start | pause | resume | stop | dock
    fan <quiet|normal|strong|max>
    raw <service> [json-params]   send an arbitrary service request

Credentials may also come from NARWAL_EMAIL / NARWAL_PASSWORD.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

import aiohttp

from . import commands as cmd
from .cloud import NarwalAuthError, NarwalCloud, NarwalCloudError
from .ws import NarwalWebsocket


async def _connect(cloud: NarwalCloud, http: aiohttp.ClientSession) -> NarwalWebsocket:
    robots = await cloud.get_robots()
    if not robots:
        raise NarwalCloudError("no robots bound to this account")
    robot = robots[0]
    ws = NarwalWebsocket(http, cloud.ws_base, robot.machine_id, cloud.session.token)
    await ws.connect()
    return ws


async def run(args: argparse.Namespace) -> int:
    email = args.email or os.environ.get("NARWAL_EMAIL", "")
    password = args.password or os.environ.get("NARWAL_PASSWORD", "")
    if not email or not password:
        print("error: provide --email/--password or NARWAL_EMAIL/NARWAL_PASSWORD", file=sys.stderr)
        return 2
    async with aiohttp.ClientSession() as http:
        cloud = NarwalCloud(http, region=args.region)
        try:
            await cloud.login(email, password)
        except NarwalAuthError as exc:
            print(f"login failed: {exc}", file=sys.stderr)
            return 1

        if args.command == "robots":
            for r in await cloud.get_robots():
                print(f"{r.device_id}  machine_id={r.machine_id}  name={r.name!r}  model={r.model}  fw={r.firmware}")
            return 0

        ws = await _connect(cloud, http)
        print(f"connected; ws={cloud.ws_base}")
        try:
            if args.command in ("status", "watch"):
                try:
                    result = await ws.get_status()
                    print(json.dumps(result, indent=1))
                except Exception as exc:  # noqa: BLE001
                    print(f"status request got no reply ({exc}); robot may be offline/idle")
                if args.command == "watch":
                    print("watching for updates (Ctrl-C to stop)...")
                    await asyncio.sleep(args.seconds)
            elif args.command in cmd.ACTIONS:
                await ws.send_command(cmd.ACTIONS[args.command])
                print(f"sent {args.command} -> {cmd.ACTIONS[args.command]}")
            elif args.command == "fan":
                await ws.set_fan_speed(args.fan)
                print(f"set fan speed {args.fan}")
            elif args.command == "raw":
                params = json.loads(args.params) if args.params else {}
                res = await ws.request(args.service, params)
                print(json.dumps(res, indent=1))
        finally:
            await ws.disconnect()
        return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Narwal T10 cloud CLI")
    p.add_argument("--email")
    p.add_argument("--password")
    p.add_argument("--region", default="us")
    p.add_argument("--seconds", type=int, default=60)
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("robots", "status", "watch", "start", "pause", "resume", "stop", "dock"):
        sub.add_parser(name)
    fan = sub.add_parser("fan")
    fan.add_argument("fan", help="quiet|normal|strong|max")
    raw = sub.add_parser("raw")
    raw.add_argument("service")
    raw.add_argument("params", nargs="?", default="")
    args = p.parse_args(argv)
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
