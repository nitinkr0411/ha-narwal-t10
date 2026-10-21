"""Protocol constants for the Narwal T10 cloud integration.

All values verified against a live T10 account and the app's traffic (2026-10-20).
"""

from __future__ import annotations

# --- REST hosts by region (header `auth-token`, lowercase JWT) ---
API_HOSTS: dict[str, str] = {
    "us": "usaclient.narwaltech.com",
    "au": "au-app.narwaltech.com",
    "global": "app.narwaltech.com",
}
DEFAULT_REGION = "us"

# WebSocket host by region + the fixed path.
WS_HOSTS: dict[str, str] = {
    "us": "usawebsocket.narwaltech.com",
    "au": "auwebsocket.narwaltech.com",
    "global": "websocket.narwaltech.com",
}
WS_PATH = "/app_websocket"

# --- REST paths (verified) ---
PATH_LOGIN = "/user/email/login/pw/"
PATH_ROBOT_LIST = "/robot/"
PATH_ROBOT_INFO = "/robot/info/"  # ?machine_id=<mac>

AUTH_HEADER = "auth-token"
APP_AUTH_HEADER = "APP-AUTH"

# --- WebSocket services (verified: status; commands from app strings) ---
SVC_INFO_ALL = "/pita/info/all"  # full status snapshot
SVC_COMMAND = "/pita_clean_system/command"  # start/stop/pause/continue/dock
SVC_SET_SWEEP_STRENGTH = "/pita/config/set_sweep_strength"  # fan/suction
SVC_SET_VOLUME = "/pita/info/volume/set"
SVC_REBOOT = "/pita/other/reboot"

# Integer command codes for SVC_COMMAND params: {"cmd": <int>}.
# Verified live on a Narwal T10 (2026-10-20) by observing robot_status/task_name
# from a known baseline (the command alone caused the change):
#   1  -> toggle dock/undock, depending on the robot's current location:
#           docked   -> ExitBase (leave the dock), robot_status 700
#           off-dock -> Summon -> returns to the dock and charges, robot_status 600
#   3  -> pause, robot_status 301 (task retained)
#   4  -> stop/end task, back to idle (robot_status 100, main_task cleared)
#   5  -> start cleaning (SysStartOperation -> RoomClean), robot_status 300
# Codes 2 and 6-30 produced no useful effect in the states tested; cmd 11 only
# moves the robot to robot_status 800 (a cleaning sub-state), it does not recall.
CMD_UNDOCK = 1
CMD_DOCK = 1  # same toggle; when the robot is OFF the dock it returns and charges
CMD_PAUSE = 3
CMD_STOP = 4
CMD_START = 5
CMD_CONTINUE = 5  # resume uses the start code; distinct resume code not observed

# Fan / suction strength values (mode_strength in status). CONFIRM extra levels.
STRENGTH_LEVELS = {
    "quiet": "silent_mode",
    "normal": "normal_mode",
    "strong": "powerful_mode",
    "max": "super_powerful_mode",
}
STRENGTH_TO_FAN = {v: k for k, v in STRENGTH_LEVELS.items()}

# WebSocket timing
KEEPALIVE_INTERVAL = 20.0
RECONNECT_BACKOFF_MAX = 60.0
STATUS_POLL_FALLBACK = 30.0  # seconds between polls while docked/idle
# While the robot is working, poll ~1/s like the official app. The robot
# BROADCASTS /pita/map (live pose + path) to every connected session, but only
# keeps streaming while a session polls /pita/info/all at the app's ~1 Hz
# cadence; at 4 s the stream stalls (captured from the app over WireGuard:
# the app sends nothing but /pita/info/all polls + commands, no map "subscribe").
ACTIVE_POLL = 1.0  # seconds between polls while the robot is working
REQUEST_TIMEOUT = 10.0
