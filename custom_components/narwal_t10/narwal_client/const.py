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

# Command verbs for SVC_COMMAND params. CONFIRM against a live (active) robot;
# derived from app string constants (Stop_Clean, Back_Wash, Task_*).
CMD_START = "Start_Clean"
CMD_PAUSE = "Pause_Clean"
CMD_CONTINUE = "Continue_Clean"
CMD_STOP = "Stop_Clean"
CMD_DOCK = "Back_Wash"  # return to dock / washstation

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
STATUS_POLL_FALLBACK = 30.0
REQUEST_TIMEOUT = 10.0
