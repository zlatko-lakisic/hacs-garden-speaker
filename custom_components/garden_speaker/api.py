"""Async client for the Garden Speaker Control API."""

from __future__ import annotations

import json
from typing import Any

import aiohttp


class GardenSpeakerError(Exception):
    """Base Garden Speaker API error."""


class GardenSpeakerAuthError(GardenSpeakerError):
    """Raised when the API rejects the configured key."""


class GardenSpeakerConnectionError(GardenSpeakerError):
    """Raised when the Control API cannot be reached."""


class GardenSpeakerApiError(GardenSpeakerError):
    """Raised when the Control API returns an error."""


class GardenSpeakerApi:
    """Client for one Garden Speaker Control API."""

    def __init__(
        self,
        host: str,
        port: int,
        api_key: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the API client."""
        self.host = host
        self.port = port
        self._api_key = api_key
        self._session = session

    @property
    def base_url(self) -> str:
        """Return the API base URL."""
        return f"http://{self.host}:{self.port}/api/v1"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Make one request and return its JSON object."""
        headers = {"X-API-Key": self._api_key} if self._api_key else {}
        try:
            async with self._session.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                json=body,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                if response.status in (401, 403):
                    raise GardenSpeakerAuthError("The Control API rejected the API key")
                if response.status >= 400:
                    detail = await response.text()
                    raise GardenSpeakerApiError(
                        f"Control API returned HTTP {response.status}: {detail[:300]}"
                    )
                if response.content_length == 0:
                    return {}
                raw = await response.text()
                if not raw.strip():
                    return {}
                try:
                    payload = json.loads(raw)
                except ValueError as err:
                    raise GardenSpeakerApiError(
                        f"Control API returned non-JSON: {raw[:200]}"
                    ) from err
                # Stack restart (and a few other endpoints) return a JSON array.
                if isinstance(payload, list):
                    return {"items": payload}
                if isinstance(payload, dict):
                    return payload
                raise GardenSpeakerApiError(
                    f"Control API returned an unexpected response ({type(payload).__name__})"
                )
        except GardenSpeakerError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise GardenSpeakerConnectionError(
                f"Cannot reach the Garden Speaker Control API at {self.host}:{self.port}"
            ) from err

    async def health_check(self) -> dict[str, Any]:
        """Run the full, side-effect-free health check."""
        return await self._request("GET", "/health/check", timeout=30)

    async def repair(self) -> dict[str, Any]:
        """Run a soft health repair."""
        return await self._request("POST", "/health/repair", body={}, timeout=180)

    async def repair_pairing(self) -> dict[str, Any]:
        """Remove and recreate Bluetooth pairing."""
        return await self._request("POST", "/bluetooth/repair", body={}, timeout=200)

    async def restart_stack(
        self, *, include_control_api: bool = False
    ) -> dict[str, Any]:
        """Restart the managed audio stack."""
        return await self._request(
            "POST",
            "/services/stack/restart",
            body={"include_control_api": include_control_api},
            timeout=180,
        )
