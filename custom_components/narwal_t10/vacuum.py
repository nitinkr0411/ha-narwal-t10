"""Vacuum entity for the Narwal T10 (cloud)."""

from __future__ import annotations

import logging

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import NarwalCoordinator
from .entity import NarwalEntity
from .ha_const import DOMAIN
from .narwal_client import commands as cmd
from .narwal_client.const import STRENGTH_LEVELS
from .narwal_client.models import RobotStatus

_LOGGER = logging.getLogger(__name__)

_FAN_LIST = list(STRENGTH_LEVELS)  # quiet/normal/strong/max


def _activity(s: RobotStatus) -> VacuumActivity | None:
    if s is None:
        return None
    if s.error_code:
        return VacuumActivity.ERROR
    if s.docked or s.charging:
        return VacuumActivity.DOCKED
    # work_status: 0 observed when idle/docked; non-zero => active. Returning-to-dock
    # vs cleaning cannot be told apart reliably until confirmed on an active robot.
    if s.work_status:
        return VacuumActivity.CLEANING
    return VacuumActivity.IDLE


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: NarwalCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NarwalVacuum(coordinator)])


class NarwalVacuum(NarwalEntity, StateVacuumEntity):
    _attr_name = None
    _attr_fan_speed_list = _FAN_LIST
    _attr_supported_features = (
        VacuumEntityFeature.START
        | VacuumEntityFeature.PAUSE
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.FAN_SPEED
        | VacuumEntityFeature.STATE
    )

    def __init__(self, coordinator: NarwalCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_vacuum"

    @property
    def activity(self) -> VacuumActivity | None:
        return _activity(self.coordinator.data)


    @property
    def fan_speed(self) -> str | None:
        return self.coordinator.data.fan_speed if self.coordinator.data else None

    async def async_start(self) -> None:
        await self.coordinator.async_command(cmd.ACTIONS["start"])

    async def async_pause(self) -> None:
        await self.coordinator.async_command(cmd.ACTIONS["pause"])

    async def async_stop(self, **kwargs) -> None:
        await self.coordinator.async_command(cmd.ACTIONS["stop"])

    async def async_return_to_base(self, **kwargs) -> None:
        await self.coordinator.async_command(cmd.ACTIONS["dock"])

    async def async_set_fan_speed(self, fan_speed: str, **kwargs) -> None:
        await self.coordinator.async_set_fan(fan_speed)
