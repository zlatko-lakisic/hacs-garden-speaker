"""Garden Speaker Home Assistant integration."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import GardenSpeakerApi
from .const import CONF_API_KEY, CONF_PORT, DOMAIN
from .coordinator import GardenSpeakerConfigEntry, GardenSpeakerCoordinator
from .services import async_setup_services, async_unload_services

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(
    hass: HomeAssistant, entry: GardenSpeakerConfigEntry
) -> bool:
    """Set up Garden Speaker from a config entry."""
    api = GardenSpeakerApi(
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data.get(CONF_API_KEY, ""),
        async_get_clientsession(hass),
    )
    coordinator = GardenSpeakerCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_setup_services(hass)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: GardenSpeakerConfigEntry
) -> bool:
    """Unload a Garden Speaker config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            await async_unload_services(hass)
            hass.data.pop(DOMAIN, None)
    return unload_ok
