"""Home Assistant services for Garden Speaker."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .api import GardenSpeakerError
from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_CONFIRM_PAIRING_MODE,
    ATTR_INCLUDE_CONTROL_API,
    DOMAIN,
    PAIRING_INSTRUCTIONS,
    SERVICE_HEALTH_CHECK,
    SERVICE_REPAIR,
    SERVICE_REPAIR_PAIRING,
    SERVICE_RESTART_STACK,
)
from .coordinator import GardenSpeakerCoordinator

ENTRY_SERVICE_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string}
)
PAIRING_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_CONFIRM_PAIRING_MODE): cv.boolean,
    }
)
RESTART_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional(ATTR_INCLUDE_CONTROL_API, default=False): cv.boolean,
    }
)


def _coordinator_for_call(
    hass: HomeAssistant, call: ServiceCall
) -> GardenSpeakerCoordinator:
    """Resolve the target coordinator for a service call."""
    coordinators: dict[str, GardenSpeakerCoordinator] = hass.data.get(DOMAIN, {})
    entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
    if entry_id:
        coordinator = coordinators.get(entry_id)
        if coordinator is None:
            raise ServiceValidationError(
                "The selected Garden Speaker config entry is not loaded"
            )
        return coordinator
    if len(coordinators) != 1:
        raise ServiceValidationError(
            "Select a Garden Speaker config entry when more than one is configured"
        )
    return next(iter(coordinators.values()))


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, SERVICE_HEALTH_CHECK):
        return

    async def handle_health_check(call: ServiceCall) -> None:
        coordinator = _coordinator_for_call(hass, call)
        await coordinator.async_refresh()
        if not coordinator.last_update_success:
            raise HomeAssistantError("Garden Speaker health check failed")

    async def run_action(call: ServiceCall, action: str) -> None:
        coordinator = _coordinator_for_call(hass, call)
        try:
            if action == SERVICE_REPAIR:
                await coordinator.api.repair()
            elif action == SERVICE_REPAIR_PAIRING:
                if not call.data[ATTR_CONFIRM_PAIRING_MODE]:
                    raise ServiceValidationError(PAIRING_INSTRUCTIONS)
                persistent_notification.async_create(
                    hass,
                    f"{PAIRING_INSTRUCTIONS}\n\nBluetooth re-pair is now running.",
                    title="Garden Speaker pairing mode",
                    notification_id="garden_speaker_pairing",
                )
                await coordinator.api.repair_pairing()
                persistent_notification.async_create(
                    hass,
                    "Bluetooth re-pair completed. Garden Speaker health is being refreshed.",
                    title="Garden Speaker paired",
                    notification_id="garden_speaker_pairing",
                )
            elif action == SERVICE_RESTART_STACK:
                await coordinator.api.restart_stack(
                    include_control_api=call.data[ATTR_INCLUDE_CONTROL_API]
                )
        except GardenSpeakerError as err:
            if action == SERVICE_REPAIR_PAIRING:
                persistent_notification.async_create(
                    hass,
                    f"Bluetooth re-pair failed: {err}\n\n{PAIRING_INSTRUCTIONS}",
                    title="Garden Speaker re-pair failed",
                    notification_id="garden_speaker_pairing",
                )
            raise HomeAssistantError(str(err)) from err
        await coordinator.async_request_refresh()

    async def handle_repair(call: ServiceCall) -> None:
        await run_action(call, SERVICE_REPAIR)

    async def handle_repair_pairing(call: ServiceCall) -> None:
        await run_action(call, SERVICE_REPAIR_PAIRING)

    async def handle_restart_stack(call: ServiceCall) -> None:
        await run_action(call, SERVICE_RESTART_STACK)

    hass.services.async_register(
        DOMAIN,
        SERVICE_HEALTH_CHECK,
        handle_health_check,
        schema=ENTRY_SERVICE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REPAIR,
        handle_repair,
        schema=ENTRY_SERVICE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REPAIR_PAIRING,
        handle_repair_pairing,
        schema=PAIRING_SERVICE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESTART_STACK,
        handle_restart_stack,
        schema=RESTART_SERVICE_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Remove integration services when the last entry unloads."""
    for service in (
        SERVICE_HEALTH_CHECK,
        SERVICE_REPAIR,
        SERVICE_REPAIR_PAIRING,
        SERVICE_RESTART_STACK,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
