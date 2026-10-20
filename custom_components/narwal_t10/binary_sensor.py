"""Binary sensors for the Narwal T10: problem and docked."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import NarwalCoordinator
from .entity import NarwalEntity
from .ha_const import DOMAIN
from .narwal_client.models import RobotStatus


@dataclass(frozen=True, kw_only=True)
class NarwalBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[RobotStatus], bool | None]


BINARY_SENSORS: tuple[NarwalBinaryDescription, ...] = (
    NarwalBinaryDescription(
        key="problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda s: bool(s.error_code) if s.error_code is not None else None,
    ),
    NarwalBinaryDescription(
        key="docked",
        translation_key="docked",
        value_fn=lambda s: s.docked,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: NarwalCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(NarwalBinary(coordinator, d) for d in BINARY_SENSORS)


class NarwalBinary(NarwalEntity, BinarySensorEntity):
    entity_description: NarwalBinaryDescription

    def __init__(self, coordinator: NarwalCoordinator, description: NarwalBinaryDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
