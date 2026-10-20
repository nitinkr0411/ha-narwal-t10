"""Data models for the Narwal T10 cloud client."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .const import STRENGTH_TO_FAN


@dataclass(frozen=True)
class RobotDevice:
    """A robot bound to the account, from ``GET /robot/``."""

    device_id: str  # robot_id
    sn: str  # sn_number
    name: str  # robot_name
    machine_id: str = ""  # keys the cloud WS + REST info
    model: str = ""
    firmware: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


def _as_int(v: Any) -> int | None:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _as_float(v: Any) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


@dataclass(frozen=True)
class RobotStatus:
    """Parsed status from a ``/pita/info/all`` result.

    Fields are verified from live capture. ``activity`` mapping of the integer
    ``work_status`` for active states is a best-effort hypothesis to confirm on an
    active robot; docked/charging/error are reliable.
    """

    battery: int | None = None
    docked: bool | None = None
    charging: bool | None = None
    work_status: int | None = None
    robot_status: int | None = None
    robot_mode: str = ""
    cleaned_area: float | None = None
    working_progress: float | None = None
    error_code: int | None = None
    fan_speed: str | None = None  # quiet/normal/strong/max
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_result(cls, result: dict[str, Any]) -> "RobotStatus":
        battery = _as_int(result.get("battery_per"))
        if battery is not None and not 0 <= battery <= 100:
            battery = None
        strength = result.get("mode_strength")
        return cls(
            battery=battery,
            docked=bool(result["station_contact"]) if "station_contact" in result else None,
            charging=bool(result["charge_status"]) if "charge_status" in result else None,
            work_status=_as_int(result.get("work_status")),
            robot_status=_as_int(result.get("robot_status")),
            robot_mode=str(result.get("robot_mode") or ""),
            cleaned_area=_as_float(result.get("cleaned_area")),
            working_progress=_as_float(result.get("working_progress")),
            error_code=_as_int(result.get("error_code")),
            fan_speed=STRENGTH_TO_FAN.get(strength) if isinstance(strength, str) else None,
            raw=result,
        )
