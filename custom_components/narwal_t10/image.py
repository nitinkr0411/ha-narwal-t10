"""Map image entity for the Narwal T10."""

from __future__ import annotations

import logging

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import NarwalCoordinator
from .entity import NarwalEntity
from .ha_const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: NarwalCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NarwalMap(hass, coordinator)])


class NarwalMap(NarwalEntity, ImageEntity):
    """Renders the robot's room map as a PNG image."""

    _attr_name = "Map"
    _attr_content_type = "image/png"

    def __init__(self, hass: HomeAssistant, coordinator: NarwalCoordinator) -> None:
        NarwalEntity.__init__(self, coordinator)
        ImageEntity.__init__(self, hass)
        self._attr_unique_id = f"{coordinator.device_id}_map"

    @property
    def image_last_updated(self):
        return self.coordinator.map_updated

    async def async_image(self) -> bytes | None:
        png = await self.coordinator.async_get_map_png()
        if png is not None:
            self._attr_image_last_updated = dt_util.utcnow()
        return png
