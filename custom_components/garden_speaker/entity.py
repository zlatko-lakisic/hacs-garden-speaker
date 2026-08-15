"""Base entity for Garden Speaker."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GardenSpeakerCoordinator


class GardenSpeakerEntity(CoordinatorEntity[GardenSpeakerCoordinator]):
    """Base class for coordinator-backed Garden Speaker entities."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: GardenSpeakerCoordinator, key: str, name: str
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        unique_root = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{unique_root}_{key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_root)},
            name=(coordinator.data or {}).get("speaker_name", "Garden Speaker"),
            manufacturer="Mostar Designs",
            model="Garden Speaker Control API",
            configuration_url=coordinator.api.base_url.removesuffix("/api/v1"),
        )
