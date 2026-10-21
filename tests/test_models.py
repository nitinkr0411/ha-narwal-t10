"""Tests for RobotStatus parsing and command mapping."""

from narwal_client import commands
from narwal_client.const import CMD_DOCK, CMD_PAUSE, CMD_START, CMD_STOP
from narwal_client.models import RobotStatus


# A real /pita/info/all result captured from the live robot (idle, docked).
LIVE_RESULT = {
    "battery_per": 100,
    "charge_status": False,
    "cleaned_area": 0.0,
    "cur_task_type": -1,
    "error_code": 0,
    "mode_strength": "powerful_mode",
    "robot_mode": "Normal",
    "robot_status": 100,
    "station_contact": True,
    "work_status": 0,
    "working_progress": 0.0,
}


def test_from_live_result():
    s = RobotStatus.from_result(LIVE_RESULT)
    assert s.battery == 100
    assert s.docked is True
    assert s.charging is False
    assert s.fan_speed == "strong"  # powerful_mode -> strong
    assert s.cleaned_area == 0.0
    assert s.error_code == 0
    assert s.work_status == 0


def test_battery_out_of_range_dropped():
    s = RobotStatus.from_result({"battery_per": 250})
    assert s.battery is None


def test_missing_fields_tolerated():
    s = RobotStatus.from_result({})
    assert s.battery is None and s.docked is None and s.fan_speed is None


def test_command_mapping():
    # Confirmed integer codes for /pita_clean_system/command.
    assert commands.ACTIONS["start"] == CMD_START == 5
    assert commands.ACTIONS["pause"] == CMD_PAUSE == 3
    assert commands.ACTIONS["stop"] == CMD_STOP == 4
    # dock/undock are the same location-toggle code (1).
    assert commands.ACTIONS["dock"] == CMD_DOCK == 1
    assert commands.ACTIONS["undock"] == 1


def test_parse_rooms_and_layer_bits():
    from narwal_client.mapdata import parse_rooms, _room_id_of
    # single-bit values map to a room id; multi-bit are boundaries (None)
    assert _room_id_of(1) == 0
    assert _room_id_of(2) == 1
    assert _room_id_of(8) == 3
    assert _room_id_of(64) == 6
    assert _room_id_of(66) is None  # 64|2 boundary
    assert _room_id_of(0) is None
    m = {"room_attr": {"attr": [
        {"room_id": 0, "type": 4, "name": "4"},
        {"room_id": 1, "type": 1, "name": "1"},
        {"room_id": 2, "type": 3, "name": "My Den"},
        {"room_id": 5, "type": 254, "name": "-2"},  # forbidden/virtual -> dropped
    ]}}
    rooms = parse_rooms(m)
    # All segmented rooms are cleanable; unknown type -> "Room <id>", custom name kept.
    assert {r["room_id"]: r["name"] for r in rooms} == {
        0: "Kitchen", 1: "Master Bedroom", 2: "My Den", 5: "Room 5",
    }


def test_coerce_room_ids():
    import sys, types
    # import the helper without pulling in homeassistant deps
    import importlib.util, pathlib
    path = pathlib.Path("custom_components/narwal_t10/vacuum.py")
    # _coerce_room_ids is pure; exec just that function body via a tiny shim
    ns = {}
    src = path.read_text()
    start = src.index("def _coerce_room_ids")
    end = src.index("\n\n\n", start)
    exec(src[start:end], ns)
    f = ns["_coerce_room_ids"]
    assert f([0, 2]) == [0, 2]
    assert f({"rooms": [1, 3]}) == [1, 3]
    assert f({"segments": ["4", 5]}) == [4, 5]
    assert f(2) == [2]
    assert f(None) == []
    assert f({"other": [1]}) == []


def test_error_label():
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location(
        "narwal_errors", "custom_components/narwal_t10/narwal_client/errors.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.error_label(0) == "No error"
    assert mod.error_label(None) == "No error"
    assert mod.error_label(3002) == "Install dustbin."
    assert mod.error_label(2001) == "Place the robot in the base station"
    assert mod.error_label(9999) == "Error 9999"  # unmapped -> raw fallback
    # T10 uses only 2001-2019 and 3001-3022; these are not in the table
    assert "Error" in mod.error_label(1005)
    assert len(mod.ERROR_MESSAGES) == 39
