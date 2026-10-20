"""Battery, status, and cleaned-area sensors for the Narwal T10."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfArea
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import NarwalCoordinator
from .entity import NarwalEntity
from .ha_const import DOMAIN
from .narwal_client.models import RobotStatus


@dataclass(frozen=True, kw_only=True)
class NarwalSensorDescription(SensorEntityDescription):
    value_fn: Callable[[RobotStatus], object]


def _status_text(s: RobotStatus) -> str | None:
    if s.error_code:
        return "error"
    if s.docked or s.charging:
        return "charging" if s.charging else "docked"
    if s.work_status:
        return "cleaning"
    return "idle"


SENSORS: tuple[NarwalSensorDescription, ...] = (
    NarwalSensorDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.battery,
    ),
    NarwalSensorDescription(
        key="status",
        translation_key="status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_status_text,
    ),
    NarwalSensorDescription(
        key="cleaned_area",
        translation_key="cleaned_area",
        native_unit_of_measurement=UnitOfArea.SQUARE_METERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.cleaned_area,
    ),
    NarwalSensorDescription(
        key="robot_mode",
        translation_key="robot_mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.robot_mode or None,
    ),
    NarwalSensorDescription(
        key="error_code",
        translation_key="error_code",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.error_code,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: NarwalCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(NarwalSensor(coordinator, d) for d in SENSORS)


class NarwalSensor(NarwalEntity, SensorEntity):
    entity_description: NarwalSensorDescription

    def __init__(self, coordinator: NarwalCoordinator, description: NarwalSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device_id}_{description.key}"

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
