"""Config flow for Garden Speaker."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    GardenSpeakerApi,
    GardenSpeakerAuthError,
    GardenSpeakerConnectionError,
    GardenSpeakerError,
)
from .const import CONF_API_KEY, CONF_PORT, DEFAULT_HOST, DEFAULT_PORT, DOMAIN


class GardenSpeakerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Garden Speaker."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure a Garden Speaker Control API."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip().lower()
            port = user_input[CONF_PORT]
            api_key = user_input.get(CONF_API_KEY, "").strip()

            if "://" in host or "/" in host:
                errors[CONF_HOST] = "invalid_host"
            else:
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()
                api = GardenSpeakerApi(
                    host,
                    port,
                    api_key,
                    async_get_clientsession(self.hass),
                )
                try:
                    health = await api.health_check()
                except GardenSpeakerConnectionError:
                    errors["base"] = "cannot_connect"
                except GardenSpeakerAuthError:
                    errors["base"] = "invalid_auth"
                except GardenSpeakerError:
                    errors["base"] = "unknown"
                except Exception:
                    errors["base"] = "unknown"
                else:
                    return self.async_create_entry(
                        title=str(health.get("speaker_name") or "Garden Speaker"),
                        data={
                            CONF_HOST: host,
                            CONF_PORT: port,
                            CONF_API_KEY: api_key,
                        },
                    )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    default=(user_input or {}).get(CONF_HOST, DEFAULT_HOST),
                ): str,
                vol.Required(
                    CONF_PORT,
                    default=(user_input or {}).get(CONF_PORT, DEFAULT_PORT),
                ): cv.port,
                vol.Optional(
                    CONF_API_KEY,
                    default=(user_input or {}).get(CONF_API_KEY, ""),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
