"""Sensors for Garden Speaker."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import GardenSpeakerConfigEntry, GardenSpeakerCoordinator
from .entity import GardenSpeakerEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GardenSpeakerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Garden Speaker sensors."""
    async_add_entities([GardenSpeakerHealthSensor(entry.runtime_data)])


class GardenSpeakerHealthSensor(GardenSpeakerEntity, SensorEntity):
    """Overall health of the complete speaker chain."""

    _attr_icon = "mdi:speaker-wireless"

    def __init__(self, coordinator: GardenSpeakerCoordinator) -> None:
        """Initialize the health sensor."""
        super().__init__(coordinator, "health", "Health")

    @property
    def native_value(self) -> str:
        """Return ok, warn, or error."""
        return str(self.coordinator.data.get("overall", "unknown"))

    @property
    def icon(self) -> str:
        """Return an icon matching current health."""
        return {
            "ok": "mdi:check-circle",
            "warn": "mdi:alert",
            "error": "mdi:alert-circle",
        }.get(self.native_value, "mdi:help-circle")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose useful diagnostic details."""
        data = self.coordinator.data
        device = data.get("device") or {}
        pulse = data.get("pulse") or {}
        pulse_info = pulse.get("info") or {}
        owntone = data.get("owntone") or {}
        speaker_output = owntone.get("speaker_output")
        return {
            "issues": data.get("issues", []),
            "fixable_issue_count": data.get("fixable_issue_count", 0),
            "mac": data.get("mac"),
            "speaker_connected": device.get("connected"),
            "speaker_paired": device.get("paired"),
            "speaker_alias": device.get("alias"),
            "default_sink": pulse_info.get("default_sink"),
            "expected_pulse_sink": data.get("expected_pulse_sink"),
            "owntone_speaker_output": speaker_output,
            "containers": data.get("containers", []),
            "check_elapsed_ms": data.get("elapsed_ms"),
        }
