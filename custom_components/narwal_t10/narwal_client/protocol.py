"""Narwal T10 cloud WebSocket protocol: AES-128-ECB JSON frames.

Reverse-engineered and verified byte-identical against the live app (2026-10-20).

- The WebSocket at wss://usawebsocket.narwaltech.com/app_websocket carries TEXT
  messages that are ``base64( AES-128-ECB( json, zero-padded to 16 bytes ) )``.
- The connection is authenticated by the ``APP-AUTH`` request header, itself
  ``base64( AES-128-ECB( pkcs7( json{machine_id, token, version:"Av2"} ) ) )``.
- The AES key is the ASCII constant below, extracted from the app.

Requests:  {"request_id": <uuid>, "machine_id": <mac>, "service": <path>, "params": {}}
Responses: {"code": 0, "machine_id": <mac>, "request_id": <echo>, "result": {...}, ...}
"""

from __future__ import annotations

import base64
import json
import uuid
from typing import Any

from Crypto.Cipher import AES  # pycryptodome (declared in manifest requirements)

# AES-128 key extracted from the app (ASCII). Their spelling, not a typo of ours.
AES_KEY = b"narwel_app_team0"
APP_AUTH_VERSION = "Av2"


def _zeropad(data: bytes, block: int = 16) -> bytes:
    if len(data) % block == 0:
        return data
    return data + b"\x00" * (block - (len(data) % block))


def encode_frame(obj: dict[str, Any]) -> str:
    """Encode a request dict to a base64 AES-ECB WebSocket text frame."""
    raw = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    ct = AES.new(AES_KEY, AES.MODE_ECB).encrypt(_zeropad(raw))
    return base64.b64encode(ct).decode("ascii")


def decode_frame(text: str | bytes) -> dict[str, Any]:
    """Decode a base64 AES-ECB WebSocket text frame to a dict."""
    if isinstance(text, bytes):
        text = text.decode("ascii")
    raw = base64.b64decode(text)
    # Trim to a whole number of AES blocks, then strip zero padding.
    raw = raw[: len(raw) // 16 * 16]
    pt = AES.new(AES_KEY, AES.MODE_ECB).decrypt(raw).rstrip(b"\x00")
    return json.loads(pt)


def build_app_auth(machine_id: str, token: str) -> str:
    """Build the APP-AUTH header value for the WebSocket upgrade."""
    body = json.dumps(
        {"machine_id": machine_id, "token": token, "version": APP_AUTH_VERSION},
        separators=(",", ":"),
    ).encode("utf-8")
    ct = AES.new(AES_KEY, AES.MODE_ECB).encrypt(_zeropad(body))
    return base64.b64encode(ct).decode("ascii")


def build_request(machine_id: str, service: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a request object with a fresh request_id."""
    return {
        "request_id": str(uuid.uuid4()),
        "machine_id": machine_id,
        "service": service,
        "params": params or {},
    }
