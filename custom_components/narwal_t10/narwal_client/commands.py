"""Mapping of Home Assistant vacuum actions to Narwal integer command codes."""

from __future__ import annotations

from .const import CMD_CONTINUE, CMD_PAUSE, CMD_START, CMD_STOP, CMD_UNDOCK

# HA action -> integer code for the /pita_clean_system/command service ({"cmd": <int>}).
# "dock" is intentionally absent: the recharge code is not yet confirmed.
ACTIONS = {
    "start": CMD_START,
    "resume": CMD_CONTINUE,
    "pause": CMD_PAUSE,
    "stop": CMD_STOP,
    "undock": CMD_UNDOCK,
}
