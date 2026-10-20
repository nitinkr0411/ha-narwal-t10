"""Tests for RobotStatus parsing and command mapping."""

from narwal_client import commands
from narwal_client.const import CMD_DOCK, CMD_START
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
    assert commands.ACTIONS["start"] == CMD_START
    assert commands.ACTIONS["dock"] == CMD_DOCK
    assert len(set(commands.ACTIONS.values())) == 5
