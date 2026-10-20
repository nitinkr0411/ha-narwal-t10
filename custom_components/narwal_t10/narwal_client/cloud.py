"""Narwal cloud REST client: login and device discovery.

Endpoints and the ``Auth-Token`` header were extracted from the T10 app. The login
response JSON shape is a working hypothesis (see spec "Known gaps"); parsing is
defensive and tolerant of a few key spellings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from .const import (
    API_HOSTS,
    AUTH_HEADER,
    DEFAULT_REGION,
    PATH_LOGIN,
    PATH_ROBOT_INFO,
    PATH_ROBOT_LIST,
    WS_HOSTS,
    WS_PATH,
)
from .models import RobotDevice

_LOGGER = logging.getLogger(__name__)


class NarwalCloudError(Exception):
    """Base cloud error."""


class NarwalAuthError(NarwalCloudError):
    """Login failed (bad credentials)."""


def _first(data: dict[str, Any], *keys: str) -> Any:
    """Return the first present, non-empty value among keys (shape-tolerant)."""
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


@dataclass
class NarwalSession:
    """Holds the auth token and the credentials needed to re-authenticate."""

    region: str = DEFAULT_REGION
    token: str = ""
    user_id: str = ""
    email: str = ""
    password: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class NarwalCloud:
    """Async REST client for the Narwal cloud."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        region: str = DEFAULT_REGION,
    ) -> None:
        self._http = session
        self._region = region if region in API_HOSTS else DEFAULT_REGION
        self._host = API_HOSTS[self._region]
        self.session = NarwalSession(region=self._region)

    @property
    def base_url(self) -> str:
        return f"https://{self._host}"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.session.token:
            headers[AUTH_HEADER] = self.session.token
        return headers

    async def _request(
        self, method: str, path: str, *, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            async with self._http.request(
                method, url, json=json, headers=self._headers(), timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:
                text = await resp.text()
                if resp.status == 401:
                    raise NarwalAuthError(f"401 Unauthorized for {path}")
                if resp.status >= 400:
                    raise NarwalCloudError(f"HTTP {resp.status} for {path}: {text[:200]}")
                try:
                    return await _as_json(resp, text)
                except ValueError as exc:
                    raise NarwalCloudError(f"non-JSON response for {path}: {exc}") from exc
        except aiohttp.ClientError as exc:
            raise NarwalCloudError(f"connection error for {path}: {exc}") from exc

    async def login(self, email: str, password: str) -> NarwalSession:
        """Log in with email + password, storing the token on the session."""
        body = await self._request("POST", PATH_LOGIN, json={"email": email, "password": password})
        result = body.get("result", body)
        if not isinstance(result, dict):
            raise NarwalCloudError("unexpected login response shape")
        token = _first(result, "token", "access_token", "accessToken", "auth_token")
        if not token:
            code = body.get("code")
            raise NarwalAuthError(f"login did not return a token (code={code})")
        self.session.token = str(token)
        self.session.user_id = str(_first(result, "uuid", "user_id", "userId", "id") or "")
        self.session.email = email
        self.session.password = password
        self.session.extra = result
        return self.session

    async def ensure_token(self) -> str:
        """Return a valid token, re-logging in if we have credentials but no token."""
        if self.session.token:
            return self.session.token
        if self.session.email and self.session.password:
            await self.login(self.session.email, self.session.password)
            return self.session.token
        raise NarwalAuthError("no token and no stored credentials")

    @property
    def ws_base(self) -> str:
        """Cloud WebSocket URL for this region (verified: wss://<host>/app_websocket)."""
        host = WS_HOSTS.get(self._region, WS_HOSTS[DEFAULT_REGION])
        return f"wss://{host}{WS_PATH}"

    async def get_robots(self) -> list[RobotDevice]:
        """List bound robots. Shapes verified against a live T10 account (``/robot/``)."""
        await self.ensure_token()
        devices: list[RobotDevice] = []
        body = await self._request("GET", PATH_ROBOT_LIST)
        rows = _extract_rows(body.get("result", body))
        for row in rows:
            device_id = str(_first(row, "robot_id", "device_id", "deviceId", "robotId") or "")
            if not device_id:
                continue
            devices.append(
                RobotDevice(
                    device_id=device_id,
                    sn=str(_first(row, "sn_number", "sn", "serial") or device_id),
                    name=str(_first(row, "robot_name", "device_name", "name") or device_id),
                    machine_id=str(_first(row, "machine_id", "mac_id") or ""),
                    model=str(_first(row, "robot_model", "model") or ""),
                    firmware=str(_first(row, "firmware_version", "firmware") or ""),
                    raw=row,
                )
            )
        return devices

    async def get_robot_info(self, machine_id: str) -> dict[str, Any]:
        """Full robot detail, keyed by machine_id (verified endpoint shape)."""
        await self.ensure_token()
        body = await self._request("GET", f"{PATH_ROBOT_INFO}?machine_id={machine_id}")
        result = body.get("result", body)
        return result if isinstance(result, dict) else {}

    async def get_map(self, robot_id: str) -> dict[str, Any]:
        """Return the map result (``map_data``, ``room_attr``, ...) from /robot/pita/map."""
        await self.ensure_token()
        body = await self._request("GET", f"/robot/pita/map?robot_id={robot_id}")
        result = body.get("result", body)
        return result if isinstance(result, dict) else {}


async def _as_json(resp: aiohttp.ClientResponse, text: str) -> dict[str, Any]:
    import json

    data = json.loads(text) if text else {}
    if not isinstance(data, dict):
        return {"result": data}
    return data


def _extract_rows(result: Any) -> list[dict[str, Any]]:
    """Normalize the various shapes a device list may take into a list of dicts."""
    if isinstance(result, list):
        return [r for r in result if isinstance(r, dict)]
    if isinstance(result, dict):
        for key in ("list", "robots", "devices", "data", "records"):
            value = result.get(key)
            if isinstance(value, list):
                return [r for r in value if isinstance(r, dict)]
        # a single device object
        if any(k in result for k in ("device_id", "deviceId", "sn", "robot_id")):
            return [result]
    return []
