"""DataUpdateCoordinator holding the cloud session and the AES-JSON WebSocket."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .ha_const import (
    CONF_DEVICE_ID,
    CONF_EMAIL,
    CONF_MACHINE_ID,
    CONF_PASSWORD,
    CONF_REGION,
    DOMAIN,
)
from .narwal_client import NarwalCloud, NarwalCloudError, NarwalWebsocket, RobotStatus
from .narwal_client.const import ACTIVE_POLL, STATUS_POLL_FALLBACK

_LOGGER = logging.getLogger(__name__)


class NarwalCoordinator(DataUpdateCoordinator[RobotStatus]):
    """Keeps the cloud WebSocket open and exposes the latest RobotStatus."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN,
            update_interval=timedelta(seconds=STATUS_POLL_FALLBACK),
        )
        self.entry = entry
        self._http = async_get_clientsession(hass)
        self.cloud = NarwalCloud(self._http, region=entry.data.get(CONF_REGION, "us"))
        self.cloud.session.email = entry.data[CONF_EMAIL]
        self.cloud.session.password = entry.data[CONF_PASSWORD]
        self.machine_id: str = entry.data[CONF_MACHINE_ID]
        self.device_id: str = entry.data[CONF_DEVICE_ID]
        self._ws: NarwalWebsocket | None = None
        self.data = RobotStatus()
        self._map_png: bytes | None = None
        self.map_updated = None
        self._map_fetched_at: float = 0.0
        self.rooms: list[dict[str, Any]] = []
        self._base_map_data: dict[str, Any] | None = None
        self._base_map_at: float = 0.0
        self.robot_pose: dict[str, Any] | None = None
        self._last_pose_push: float = 0.0
        # Diagnostics: how many /pita/map frames the socket has delivered, and
        # when the last one carried a usable pose. Surfaced as vacuum attributes
        # so the live-map data path can be observed from the HA frontend.
        self.map_push_count: int = 0
        self.last_map_push: str | None = None

    async def async_start(self) -> None:
        # Tear down any prior socket first: the cloud allows one WS per
        # credential and the live /pita/map pushes bind to a single session, so
        # two overlapping connections kick each other off (self-contention) and
        # the live-map marker stops updating. Always leave exactly one open.
        if self._ws is not None:
            try:
                await self._ws.disconnect()
            except Exception as exc:  # noqa: BLE001
                _LOGGER.debug("stale WS teardown failed: %s", exc)
            self._ws = None
        await self.cloud.ensure_token()
        self._ws = NarwalWebsocket(
            self._http, self.cloud.ws_base, self.machine_id,
            self.cloud.session.token, on_status=self._on_status, on_map=self._on_map,
        )
        await self._ws.connect()

    async def async_stop(self) -> None:
        if self._ws is not None:
            await self._ws.disconnect()
            self._ws = None

    def _on_status(self, result: dict[str, Any]) -> None:
        status = RobotStatus.from_result(result)
        if status.docked:
            self.robot_pose = None  # hide the live marker once home
        self.async_set_updated_data(status)

    def _on_map(self, result: dict[str, Any]) -> None:
        """Live robot pose pushed over /pita/map while cleaning."""
        import time

        from homeassistant.util import dt as dt_util

        self.map_push_count += 1
        x, y = result.get("x"), result.get("y")
        if x is None or y is None:
            return
        self.last_map_push = dt_util.utcnow().isoformat()
        self.robot_pose = {"x": x, "y": y, "theta": result.get("theta")}
        # Throttle map re-renders; pushes arrive a few times per second.
        now = time.monotonic()
        if now - self._last_pose_push < 1.5:
            return
        self._last_pose_push = now
        self.map_updated = dt_util.utcnow()
        self.async_update_listeners()

    def _retune_interval(self, status: RobotStatus) -> None:
        """Poll fast while the robot is working, slowly while it is docked/idle."""
        active = bool(status) and (
            (status.docked is False)
            or bool(status.work_status)
            or (status.robot_status not in (None, 100, 301))
        )
        wanted = timedelta(seconds=ACTIVE_POLL if active else STATUS_POLL_FALLBACK)
        if self.update_interval != wanted:
            self.update_interval = wanted

    async def _async_update_data(self) -> RobotStatus:
        """Polling fallback: request a status snapshot; keep last known on failure."""
        try:
            if self._ws is None or not self._ws.connected:
                await self.async_start()
            result = await self._ws.get_status()  # type: ignore[union-attr]
            if not self.rooms:
                # Prime the room list once so entities can expose rooms without
                # waiting for the map image to be rendered.
                await self.async_get_map_png()
            status = RobotStatus.from_result(result)
            self._retune_interval(status)
            return status
        except NarwalCloudError as exc:
            raise UpdateFailed(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            # Idle robots disconnect from the cloud; keep the last snapshot and
            # slow the polling back down.
            _LOGGER.debug("status poll failed (robot may be idle): %s", exc)
            self.update_interval = timedelta(seconds=STATUS_POLL_FALLBACK)
            return self.data

    async def async_get_map_png(self):
        """Fetch + render the room map as PNG, cached for ~2 minutes."""
        import time

        from homeassistant.util import dt as dt_util

        from .narwal_client.mapdata import parse_rooms, render_png

        now = time.monotonic()
        # Refresh the static base map (rooms/walls) occasionally; it only changes
        # when the robot remaps. The live robot marker is overlaid on every render.
        if self._base_map_data is None or (now - self._base_map_at) > 120:
            try:
                result = await self.cloud.get_map(self.device_id)
                md = result.get("map_data") if isinstance(result, dict) else None
                if isinstance(result, dict):
                    self.rooms = parse_rooms(result)
                if md and md.get("room_layer"):
                    self._base_map_data = md
                    self._base_map_at = now
                    if self.map_updated is None:
                        self.map_updated = dt_util.utcnow()
            except Exception as exc:  # noqa: BLE001
                _LOGGER.debug("map fetch failed: %s", exc)
        if not self._base_map_data:
            return self._map_png
        try:
            self._map_png = await self.hass.async_add_executor_job(
                render_png, self._base_map_data, 4, self.rooms, self.robot_pose
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("map render failed: %s", exc)
        return self._map_png

    async def _refresh_soon(self) -> None:
        # Pick up the new state quickly and let the poll interval re-tune to fast.
        self.update_interval = timedelta(seconds=ACTIVE_POLL)
        await self.async_request_refresh()

    async def async_command(self, code: int) -> None:
        if self._ws is None or not self._ws.connected:
            await self.async_start()
        await self._ws.send_command(code)  # type: ignore[union-attr]
        await self._refresh_soon()

    async def async_set_fan(self, level: str) -> None:
        if self._ws is None or not self._ws.connected:
            await self.async_start()
        await self._ws.set_fan_speed(level)  # type: ignore[union-attr]
        await self._refresh_soon()

    async def async_clean_rooms(self, room_ids: list[int]) -> None:
        if self._ws is None or not self._ws.connected:
            await self.async_start()
        await self._ws.clean_rooms(room_ids)  # type: ignore[union-attr]
        await self._refresh_soon()
