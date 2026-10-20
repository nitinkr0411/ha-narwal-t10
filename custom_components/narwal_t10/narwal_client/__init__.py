"""Standalone Narwal T10 cloud client (Home Assistant independent).

Protocol: REST login/discovery + a cloud WebSocket carrying AES-128-ECB JSON
frames. Reverse-engineered and verified against the live app.
"""

from __future__ import annotations

from . import commands, protocol
from .cloud import NarwalAuthError, NarwalCloud, NarwalCloudError, NarwalSession
from .models import RobotDevice, RobotStatus
from .protocol import build_app_auth, decode_frame, encode_frame
from .ws import NarwalWebsocket, NarwalWsError

__all__ = [
    "NarwalCloud",
    "NarwalSession",
    "NarwalCloudError",
    "NarwalAuthError",
    "NarwalWebsocket",
    "NarwalWsError",
    "RobotDevice",
    "RobotStatus",
    "build_app_auth",
    "encode_frame",
    "decode_frame",
    "commands",
    "protocol",
]
