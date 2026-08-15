"""Binary sensors for Garden Speaker."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import GardenSpeakerConfigEntry, GardenSpeakerCoordinator
from .entity import GardenSpeakerEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GardenSpeakerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Garden Speaker binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            GardenSpeakerConnectedSensor(coordinator),
            GardenSpeakerOutputSelectedSensor(coordinator),
        ]
    )


class GardenSpeakerConnectedSensor(GardenSpeakerEntity, BinarySensorEntity):
    """Whether the Bluetooth speaker is connected."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: GardenSpeakerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "speaker_connected", "Speaker connected")

    @property
    def is_on(self) -> bool:
        """Return whether the speaker is connected."""
        return bool((self.coordinator.data.get("device") or {}).get("connected"))


class GardenSpeakerOutputSelectedSensor(GardenSpeakerEntity, BinarySensorEntity):
    """Whether OwnTone has selected the speaker output."""

    _attr_icon = "mdi:audio-input-rca"

    def __init__(self, coordinator: GardenSpeakerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "owntone_output_selected", "OwnTone output selected")

    @property
    def is_on(self) -> bool:
        """Return whether the live PulseAudio output is selected."""
        output = (self.coordinator.data.get("owntone") or {}).get("speaker_output")
        return bool(output and output.get("selected"))
