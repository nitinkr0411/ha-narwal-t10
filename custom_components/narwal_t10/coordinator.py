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
from .narwal_client.const import STATUS_POLL_FALLBACK

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

    async def async_start(self) -> None:
        await self.cloud.ensure_token()
        self._ws = NarwalWebsocket(
            self._http, self.cloud.ws_base, self.machine_id,
            self.cloud.session.token, on_status=self._on_status,
        )
        await self._ws.connect()

    async def async_stop(self) -> None:
        if self._ws is not None:
            await self._ws.disconnect()
            self._ws = None

    def _on_status(self, result: dict[str, Any]) -> None:
        self.async_set_updated_data(RobotStatus.from_result(result))

    async def _async_update_data(self) -> RobotStatus:
        """Polling fallback: request a status snapshot; keep last known on failure."""
        try:
            if self._ws is None or not self._ws.connected:
                await self.async_start()
            result = await self._ws.get_status()  # type: ignore[union-attr]
            return RobotStatus.from_result(result)
        except NarwalCloudError as exc:
            raise UpdateFailed(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            # Idle robots disconnect from the cloud; keep the last snapshot.
            _LOGGER.debug("status poll failed (robot may be idle): %s", exc)
            return self.data

    async def async_get_map_png(self):
        """Fetch + render the room map as PNG, cached for ~2 minutes."""
        import time

        from homeassistant.util import dt as dt_util

        from .narwal_client.mapdata import render_png

        now = time.monotonic()
        if self._map_png is not None and (now - self._map_fetched_at) < 120:
            return self._map_png
        try:
            result = await self.cloud.get_map(self.device_id)
            md = result.get("map_data") if isinstance(result, dict) else None
            if md and md.get("room_layer"):
                png = await self.hass.async_add_executor_job(render_png, md)
                self._map_png = png
                self._map_fetched_at = now
                self.map_updated = dt_util.utcnow()
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("map fetch/render failed: %s", exc)
        return self._map_png

    async def async_command(self, verb: str) -> None:
        if self._ws is None or not self._ws.connected:
            await self.async_start()
        await self._ws.send_command(verb)  # type: ignore[union-attr]

    async def async_set_fan(self, level: str) -> None:
        if self._ws is None or not self._ws.connected:
            await self.async_start()
        await self._ws.set_fan_speed(level)  # type: ignore[union-attr]
