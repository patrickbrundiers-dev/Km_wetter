"""DataUpdateCoordinator für Kachelmannwetter."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    KachelmannApi,
    KachelmannAuthError,
    KachelmannError,
    KachelmannForbiddenError,
    KachelmannRateLimitError,
)
from .const import DOMAIN, EXT_REFRESH, TREND_REFRESH

_LOGGER = logging.getLogger(__name__)


def _as_list(data: Any) -> list[dict[str, Any]]:
    """Die API liefert 'data' je nach Endpunkt als Liste oder als Objekt."""
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    if isinstance(data, dict):
        return [d for d in data.values() if isinstance(d, dict)]
    return []


def _flatten_current(data: Any) -> dict[str, Any]:
    """{name: {value: ...}} oder [{name, value}] -> {name: value}."""
    result: dict[str, Any] = {}
    if isinstance(data, dict):
        for key, item in data.items():
            result[key] = item.get("value") if isinstance(item, dict) else item
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "name" in item:
                result[item["name"]] = item.get("value")
    return result


class KachelmannCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Holt aktuelle Werte, Stundenvorhersage und 14-Tage-Trend."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: KachelmannApi,
        lat: float,
        lon: float,
        interval_minutes: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=interval_minutes),
        )
        self.api = api
        self.lat = lat
        self.lon = lon
        self._trend: list[dict[str, Any]] = []
        self._trend_fetched: datetime | None = None
        self._ext: dict[str, list[dict[str, Any]]] = {}
        self._ext_fetched: datetime | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            current_raw = await self.api.async_get_current(self.lat, self.lon)
            hourly_raw = await self.api.async_get_hourly(self.lat, self.lon)

            now = dt_util.utcnow()
            if self._trend_fetched is None or now - self._trend_fetched > TREND_REFRESH:
                try:
                    trend_raw = await self.api.async_get_trend(self.lat, self.lon)
                    self._trend = _as_list(trend_raw.get("data"))
                    self._trend_fetched = now
                except KachelmannRateLimitError:
                    raise
                except KachelmannError as err:
                    # Trend ist optional - alte Daten behalten
                    _LOGGER.debug("Trend konnte nicht geladen werden: %s", err)
            if self._ext_fetched is None or now - self._ext_fetched > EXT_REFRESH:
                for interval in ("3h", "6h"):
                    try:
                        raw = await self.api.async_get_interval(
                            self.lat, self.lon, interval
                        )
                        self._ext[interval] = _as_list(raw.get("data"))
                    except KachelmannRateLimitError:
                        raise
                    except KachelmannError as err:
                        # Optional - alte Daten behalten
                        _LOGGER.debug("%s-Vorhersage nicht geladen: %s", interval, err)
                self._ext_fetched = now
        except KachelmannAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except KachelmannForbiddenError as err:
            raise UpdateFailed(
                "403: Koordinaten stimmen nicht mit einem in deinem Konto "
                "hinterlegten API-Standort überein"
            ) from err
        except KachelmannRateLimitError as err:
            raise UpdateFailed(f"{err} - bitte Update-Intervall erhöhen") from err
        except KachelmannError as err:
            raise UpdateFailed(str(err)) from err

        hourly = _as_list(hourly_raw.get("data"))
        return {
            "current": _flatten_current(current_raw.get("data")),
            "hourly": hourly,
            "extended": self._merge_extended(hourly),
            "daily": self._trend,
            "alt": current_raw.get("alt"),
        }

    def _merge_extended(self, hourly: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """1h-Werte, danach 3h-Raster, danach 6h-Raster (jeweils nur Späteres)."""
        out = list(hourly)
        for interval, hours in (("3h", 3), ("6h", 6)):
            last = max(
                (dt_util.parse_datetime(str(i.get("dateTime", ""))) for i in out),
                default=None,
                key=lambda d: d.timestamp() if d else 0,
            )
            for item in self._ext.get(interval, []):
                ts = dt_util.parse_datetime(str(item.get("dateTime", "")))
                if ts is None or (last is not None and ts <= last):
                    continue
                out.append({**item, "_step": hours})
        return out
