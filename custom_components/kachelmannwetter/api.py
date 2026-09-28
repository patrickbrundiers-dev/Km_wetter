"""Asynchroner Client für die Kachelmannwetter-API (v02)."""
from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from .const import API_BASE_URL, API_TIMEOUT


class KachelmannError(Exception):
    """Allgemeiner API-Fehler."""


class KachelmannAuthError(KachelmannError):
    """API-Key ungültig (401)."""


class KachelmannForbiddenError(KachelmannError):
    """Key gültig, aber Standort nicht freigeschaltet (403)."""


class KachelmannRateLimitError(KachelmannError):
    """Tageslimit erreicht (429)."""


class KachelmannApi:
    """Kleiner Wrapper um die REST-API."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str) -> None:
        self._session = session
        self._api_key = api_key
        self.rate_limit_remaining: int | None = None

    async def _get(self, path: str) -> dict[str, Any]:
        url = f"{API_BASE_URL}{path}"
        headers = {"Accept": "application/json", "X-API-Key": self._api_key}
        params = {"units": "metric"}
        try:
            async with asyncio.timeout(API_TIMEOUT):
                async with self._session.get(
                    url, headers=headers, params=params
                ) as resp:
                    remaining = resp.headers.get("x-ratelimit-remaining")
                    if remaining is not None and remaining.isdigit():
                        self.rate_limit_remaining = int(remaining)
                    if resp.status == 401:
                        raise KachelmannAuthError("Ungültiger API-Key")
                    if resp.status == 403:
                        raise KachelmannForbiddenError(
                            "Standort nicht in den API-Standorten hinterlegt"
                        )
                    if resp.status == 429:
                        raise KachelmannRateLimitError("Tageslimit erreicht")
                    if resp.status >= 400:
                        raise KachelmannError(f"HTTP {resp.status}")
                    return await resp.json(content_type=None)
        except TimeoutError as err:
            raise KachelmannError("Zeitüberschreitung bei der API-Anfrage") from err
        except aiohttp.ClientError as err:
            raise KachelmannError(f"Verbindungsfehler: {err}") from err

    async def async_get_current(self, lat: float, lon: float) -> dict[str, Any]:
        return await self._get(f"/current/{lat}/{lon}")

    async def async_get_hourly(self, lat: float, lon: float) -> dict[str, Any]:
        return await self._get(f"/forecast/{lat}/{lon}/advanced/1h")

    async def async_get_trend(self, lat: float, lon: float) -> dict[str, Any]:
        return await self._get(f"/forecast/{lat}/{lon}/trend14days")
