"""Async WebSocket client for the Narwal T10 cloud (JSON over AES-ECB)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import aiohttp

from .const import (
    APP_AUTH_HEADER,
    REQUEST_TIMEOUT,
    SVC_COMMAND,
    SVC_INFO_ALL,
    SVC_SET_SWEEP_STRENGTH,
    STRENGTH_LEVELS,
)
from .protocol import build_app_auth, build_request, decode_frame, encode_frame

_LOGGER = logging.getLogger(__name__)

StatusCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


class NarwalWsError(Exception):
    """WebSocket error."""


class NarwalWebsocket:
    """Maintains the cloud WebSocket and correlates request/response by request_id."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        ws_url: str,
        machine_id: str,
        token: str,
        *,
        on_status: StatusCallback | None = None,
    ) -> None:
        self._http = session
        self._url = ws_url
        self._machine_id = machine_id
        self._token = token
        self._on_status = on_status
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._recv_task: asyncio.Task | None = None
        self._pending: dict[str, asyncio.Future] = {}

    @property
    def connected(self) -> bool:
        return self._ws is not None and not self._ws.closed

    async def connect(self) -> None:
        headers = {APP_AUTH_HEADER: build_app_auth(self._machine_id, self._token)}
        self._ws = await self._http.ws_connect(
            self._url, headers=headers, heartbeat=25,
            timeout=aiohttp.ClientWSTimeout(ws_close=15),
        )
        self._recv_task = asyncio.ensure_future(self._receive_loop())
        _LOGGER.info("Narwal cloud WebSocket connected")

    async def disconnect(self) -> None:
        if self._recv_task:
            self._recv_task.cancel()
        if self._ws and not self._ws.closed:
            await self._ws.close()
        self._ws = None
        for fut in self._pending.values():
            if not fut.done():
                fut.cancel()
        self._pending.clear()

    async def request(
        self, service: str, params: dict[str, Any] | None = None, timeout: float = REQUEST_TIMEOUT
    ) -> dict[str, Any]:
        """Send a request and await the matching response's ``result``."""
        if not self.connected:
            raise NarwalWsError("not connected")
        req = build_request(self._machine_id, service, params)
        rid = req["request_id"]
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[rid] = fut
        try:
            assert self._ws is not None
            await self._ws.send_str(encode_frame(req))
            resp = await asyncio.wait_for(fut, timeout=timeout)
        finally:
            self._pending.pop(rid, None)
        if resp.get("code") not in (0, None):
            raise NarwalWsError(f"service {service} returned code {resp.get('code')}")
        return resp.get("result", {})

    async def get_status(self) -> dict[str, Any]:
        """Request a full status snapshot (the robot responds; verified live)."""
        return await self.request(SVC_INFO_ALL, {})

    async def send(self, service: str, params: dict[str, Any] | None = None) -> None:
        """Fire-and-forget a request frame (commands do not reliably ack)."""
        if not self.connected:
            raise NarwalWsError("not connected")
        assert self._ws is not None
        await self._ws.send_str(encode_frame(build_request(self._machine_id, service, params)))

    async def send_command(self, code: int) -> None:
        # Verified live: the command service takes {"cmd": <int>}. Codes are in
        # const.py (CMD_START=5, CMD_PAUSE=3, CMD_STOP=4, dock/undock toggle=1).
        await self.send(SVC_COMMAND, {"cmd": code})

    async def clean_rooms(self, room_ids: list[int]) -> None:
        """Start a clean restricted to the given room ids.

        Captured from the app: a room clean is the start command plus a
        ``clean_order`` list and an (empty) ``floor_type``; omitting ``floor_type``
        makes the robot ignore ``clean_order`` and clean everything.
        """
        from .const import CMD_START

        ids = [int(r) for r in room_ids]
        await self.send(SVC_COMMAND, {"cmd": CMD_START, "clean_order": ids, "floor_type": []})

    async def set_fan_speed(self, level_name: str) -> None:
        strength = STRENGTH_LEVELS.get(level_name)
        if strength is None:
            raise NarwalWsError(f"unknown fan level {level_name}")
        await self.send(SVC_SET_SWEEP_STRENGTH, {"mode_strength": strength})

    async def _receive_loop(self) -> None:
        assert self._ws is not None
        try:
            async for msg in self._ws:
                if msg.type != aiohttp.WSMsgType.TEXT:
                    if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        break
                    continue
                try:
                    obj = decode_frame(msg.data)
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.debug("undecodable frame: %s", exc)
                    continue
                rid = obj.get("request_id")
                fut = self._pending.get(rid) if rid else None
                if fut is not None and not fut.done():
                    fut.set_result(obj)
                # Any message carrying a status result updates the coordinator.
                result = obj.get("result")
                if isinstance(result, dict) and "battery_per" in result and self._on_status:
                    res = self._on_status(result)
                    if asyncio.iscoroutine(res):
                        await res
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("receive loop ended: %s", exc)
