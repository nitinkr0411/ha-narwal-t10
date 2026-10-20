"""Mapping of Home Assistant vacuum actions to Narwal command verbs."""

from __future__ import annotations

from .const import CMD_CONTINUE, CMD_DOCK, CMD_PAUSE, CMD_START, CMD_STOP

# HA action -> command verb for the /pita_clean_system/command service.
ACTIONS = {
    "start": CMD_START,
    "resume": CMD_CONTINUE,
    "pause": CMD_PAUSE,
    "stop": CMD_STOP,
    "dock": CMD_DOCK,
}
