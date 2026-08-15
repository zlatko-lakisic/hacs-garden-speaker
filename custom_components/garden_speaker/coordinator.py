"""Data update coordinator for Garden Speaker."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    GardenSpeakerApi,
    GardenSpeakerAuthError,
    GardenSpeakerConnectionError,
    GardenSpeakerError,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type GardenSpeakerConfigEntry = ConfigEntry[GardenSpeakerCoordinator]


class GardenSpeakerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the Garden Speaker health chain."""

    config_entry: GardenSpeakerConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: GardenSpeakerConfigEntry,
        api: GardenSpeakerApi,
    ) -> None:
        """Initialize the coordinator."""
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN}_{config_entry.entry_id}",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch current health data."""
        try:
            return await self.api.health_check()
        except GardenSpeakerAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except GardenSpeakerConnectionError as err:
            raise UpdateFailed(str(err)) from err
        except GardenSpeakerError as err:
            raise UpdateFailed(str(err)) from err
