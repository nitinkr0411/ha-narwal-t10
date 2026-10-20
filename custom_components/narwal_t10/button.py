"""One 'clean this room' button per room detected on the map."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import NarwalCoordinator
from .entity import NarwalEntity
from .ha_const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: NarwalCoordinator = hass.data[DOMAIN][entry.entry_id]
    # Disambiguate duplicate room names (e.g. two "Kitchen" areas).
    seen: dict[str, int] = {}
    buttons: list[NarwalRoomButton] = []
    for room in coordinator.rooms:
        name = room["name"]
        seen[name] = seen.get(name, 0) + 1
        label = name if seen[name] == 1 else f"{name} {seen[name]}"
        buttons.append(NarwalRoomButton(coordinator, room["room_id"], label))
    async_add_entities(buttons)


class NarwalRoomButton(NarwalEntity, ButtonEntity):
    _attr_icon = "mdi:broom"

    def __init__(self, coordinator: NarwalCoordinator, room_id: int, label: str) -> None:
        super().__init__(coordinator)
        self._room_id = room_id
        self._attr_name = f"Clean {label}"
        self._attr_unique_id = f"{coordinator.device_id}_clean_room_{room_id}"

    async def async_press(self) -> None:
        await self.coordinator.async_clean_rooms([self._room_id])
