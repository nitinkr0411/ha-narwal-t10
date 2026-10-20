"""Base entity for Narwal T10 entities."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import NarwalCoordinator
from .ha_const import CONF_DEVICE_NAME, DOMAIN, MANUFACTURER, MODEL


class NarwalEntity(CoordinatorEntity[NarwalCoordinator]):
    """Common device info and availability for Narwal entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NarwalCoordinator) -> None:
        super().__init__(coordinator)
        device_id = coordinator.device_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=coordinator.entry.data.get(CONF_DEVICE_NAME) or f"Narwal T10 {device_id}",
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data is not None
