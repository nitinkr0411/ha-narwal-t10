"""Mapping of Home Assistant vacuum actions to Narwal integer command codes."""

from __future__ import annotations

from .const import CMD_CONTINUE, CMD_DOCK, CMD_PAUSE, CMD_START, CMD_STOP, CMD_UNDOCK

# HA action -> integer code for the /pita_clean_system/command service ({"cmd": <int>}).
# "dock" and "undock" share code 1: it is a location-dependent toggle. The vacuum
# entity guards async_return_to_base so a docked robot is never toggled off its dock.
ACTIONS = {
    "start": CMD_START,
    "resume": CMD_CONTINUE,
    "pause": CMD_PAUSE,
    "stop": CMD_STOP,
    "undock": CMD_UNDOCK,
    "dock": CMD_DOCK,
}
