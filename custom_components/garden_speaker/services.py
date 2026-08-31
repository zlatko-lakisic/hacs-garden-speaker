"""Home Assistant services for Garden Speaker."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
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

NOTIFY_ID = "garden_speaker_action"


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


def _health_summary(data: dict[str, Any] | None) -> tuple[str, str, list[str]]:
    """Return overall label, short line, and issue bullet lines from health data."""
    data = data or {}
    overall = str(data.get("overall") or "unknown").lower()
    label = {
        "ok": "Healthy",
        "warn": "Warning",
        "warning": "Warning",
        "error": "Needs attention",
    }.get(overall, overall.capitalize() if overall else "Unknown")

    device = data.get("device") or {}
    connected = device.get("connected")
    paired = device.get("paired")
    bits: list[str] = []
    if paired is True:
        bits.append("paired")
    elif paired is False:
        bits.append("not paired")
    if connected is True:
        bits.append("BT connected")
    elif connected is False:
        bits.append("BT disconnected")
    short = label if not bits else f"{label} ({', '.join(bits)})"

    issue_lines: list[str] = []
    for issue in data.get("issues") or []:
        if not isinstance(issue, dict):
            continue
        msg = issue.get("message") or issue.get("code")
        if msg:
            issue_lines.append(str(msg))
    return label, short, issue_lines


def _notify(
    hass: HomeAssistant,
    *,
    title: str,
    message: str,
    notification_id: str = NOTIFY_ID,
) -> None:
    """Create or replace a persistent notification."""
    persistent_notification.async_create(
        hass,
        message,
        title=title,
        notification_id=notification_id,
    )


def _response_from_health(
    *,
    action: str,
    success: bool,
    data: dict[str, Any] | None,
    detail: str | None = None,
) -> ServiceResponse:
    """Build a service response dict for scripts / UI."""
    label, short, issues = _health_summary(data)
    return {
        "action": action,
        "success": success,
        "overall": (data or {}).get("overall"),
        "summary": short,
        "health_label": label,
        "issues": issues,
        "detail": detail,
    }


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, SERVICE_HEALTH_CHECK):
        return

    async def handle_health_check(call: ServiceCall) -> ServiceResponse:
        coordinator = _coordinator_for_call(hass, call)
        _notify(
            hass,
            title="Garden Speaker — Check health",
            message="Running a fresh health diagnosis…",
        )
        await coordinator.async_refresh()
        if not coordinator.last_update_success:
            _notify(
                hass,
                title="Garden Speaker — Check health failed",
                message="Health check failed. The Control API did not return a usable result.",
            )
            raise HomeAssistantError("Garden Speaker health check failed")

        label, short, issues = _health_summary(coordinator.data)
        lines = [f"Result: {short}."]
        if issues:
            lines.append("")
            lines.append("Issues:")
            lines.extend(f"• {line}" for line in issues)
        else:
            lines.append("No issues reported.")
        _notify(
            hass,
            title=f"Garden Speaker — {label}",
            message="\n".join(lines),
        )
        return _response_from_health(
            action=SERVICE_HEALTH_CHECK,
            success=True,
            data=coordinator.data,
        )

    async def run_action(call: ServiceCall, action: str) -> ServiceResponse:
        coordinator = _coordinator_for_call(hass, call)
        titles = {
            SERVICE_REPAIR: "Garden Speaker — Auto repair",
            SERVICE_REPAIR_PAIRING: "Garden Speaker — Re-pair Bluetooth",
            SERVICE_RESTART_STACK: "Garden Speaker — Restart stack",
        }
        title = titles.get(action, "Garden Speaker")
        action_detail: str | None = None
        try:
            if action == SERVICE_REPAIR:
                _notify(
                    hass,
                    title=title,
                    message="Running safe automatic repairs (pairing kept)…",
                )
                await coordinator.api.repair()
            elif action == SERVICE_REPAIR_PAIRING:
                if not call.data[ATTR_CONFIRM_PAIRING_MODE]:
                    raise ServiceValidationError(PAIRING_INSTRUCTIONS)
                _notify(
                    hass,
                    title=title,
                    message=(
                        f"{PAIRING_INSTRUCTIONS}\n\n"
                        "Bluetooth re-pair is now running. This can take up to three minutes."
                    ),
                    notification_id="garden_speaker_pairing",
                )
                await coordinator.api.repair_pairing()
            elif action == SERVICE_RESTART_STACK:
                include_api = call.data[ATTR_INCLUDE_CONTROL_API]
                _notify(
                    hass,
                    title=title,
                    message=(
                        "Restarting managed Garden Speaker services in dependency order"
                        + (" (including Control API)…" if include_api else "…")
                    ),
                )
                result = await coordinator.api.restart_stack(
                    include_control_api=include_api
                )
                items = result.get("items") if isinstance(result, dict) else None
                if isinstance(items, list) and items:
                    names = [
                        str(item.get("name") or item.get("id") or "?")
                        for item in items
                        if isinstance(item, dict)
                    ]
                    running = sum(
                        1
                        for item in items
                        if isinstance(item, dict) and item.get("running")
                    )
                    action_detail = (
                        f"Restarted {len(items)} service(s)"
                        f" ({running} running): {', '.join(names)}."
                    )
        except GardenSpeakerError as err:
            fail_title = f"{title} failed"
            fail_msg = str(err)
            if action == SERVICE_REPAIR_PAIRING:
                fail_msg = f"{fail_msg}\n\n{PAIRING_INSTRUCTIONS}"
                _notify(
                    hass,
                    title=fail_title,
                    message=fail_msg,
                    notification_id="garden_speaker_pairing",
                )
            else:
                _notify(hass, title=fail_title, message=fail_msg)
            raise HomeAssistantError(str(err)) from err

        await coordinator.async_request_refresh()
        # Give the coordinator a moment to finish the refresh when possible.
        await coordinator.async_refresh()

        label, short, issues = _health_summary(coordinator.data)
        done_lines = {
            SERVICE_REPAIR: "Auto repair finished.",
            SERVICE_REPAIR_PAIRING: "Bluetooth re-pair finished.",
            SERVICE_RESTART_STACK: "Audio stack restart finished.",
        }
        lines = [done_lines.get(action, "Action finished."), f"Health now: {short}."]
        if action_detail:
            lines.insert(1, action_detail)
        if issues:
            lines.append("")
            lines.append("Remaining issues:")
            lines.extend(f"• {line}" for line in issues)
        notify_id = (
            "garden_speaker_pairing"
            if action == SERVICE_REPAIR_PAIRING
            else NOTIFY_ID
        )
        _notify(
            hass,
            title=f"{title} — {label}",
            message="\n".join(lines),
            notification_id=notify_id,
        )
        return _response_from_health(
            action=action,
            success=True,
            data=coordinator.data,
            detail=action_detail or done_lines.get(action),
        )

    async def handle_repair(call: ServiceCall) -> ServiceResponse:
        return await run_action(call, SERVICE_REPAIR)

    async def handle_repair_pairing(call: ServiceCall) -> ServiceResponse:
        return await run_action(call, SERVICE_REPAIR_PAIRING)

    async def handle_restart_stack(call: ServiceCall) -> ServiceResponse:
        return await run_action(call, SERVICE_RESTART_STACK)

    hass.services.async_register(
        DOMAIN,
        SERVICE_HEALTH_CHECK,
        handle_health_check,
        schema=ENTRY_SERVICE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REPAIR,
        handle_repair,
        schema=ENTRY_SERVICE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REPAIR_PAIRING,
        handle_repair_pairing,
        schema=PAIRING_SERVICE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESTART_STACK,
        handle_restart_stack,
        schema=RESTART_SERVICE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
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
