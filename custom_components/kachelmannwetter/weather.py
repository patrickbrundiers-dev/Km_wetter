"""Wetter-Entität mit stündlicher und täglicher Vorhersage."""
from __future__ import annotations

from typing import Any

from homeassistant.components.weather import (
    Forecast,
    SingleCoordinatorWeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.const import (
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import KachelmannConfigEntry
from .const import DOMAIN, SYMBOL_TO_CONDITION
from .coordinator import KachelmannCoordinator


def symbol_to_condition(symbol: str | None, is_day: bool | None = True) -> str | None:
    """Kachelmann-weatherSymbol in einen HA-Wetterzustand übersetzen."""
    if not symbol:
        return None
    night = symbol.endswith("_night")
    base = symbol.removesuffix("_night")
    condition = SYMBOL_TO_CONDITION.get(base)
    if condition == "sunny" and (night or is_day is False):
        return "clear-night"
    return condition


def device_info(entry: KachelmannConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="Meteologix AG / Kachelmann Gruppe",
        model="Wetter-API v02",
        entry_type=DeviceEntryType.SERVICE,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KachelmannConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([KachelmannWeather(entry.runtime_data, entry)])


class KachelmannWeather(SingleCoordinatorWeatherEntity[KachelmannCoordinator]):
    """Wetter-Entität."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_attribution = "Wetterdaten von Meteologix AG / Kachelmann Gruppe"
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
    _attr_native_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY
    )

    def __init__(
        self, coordinator: KachelmannCoordinator, entry: KachelmannConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_weather"
        self._attr_device_info = device_info(entry)

    @property
    def _current(self) -> dict[str, Any]:
        return self.coordinator.data.get("current", {})

    @property
    def _first_hour(self) -> dict[str, Any]:
        hourly = self.coordinator.data.get("hourly", [])
        return hourly[0] if hourly else {}

    @property
    def native_temperature(self) -> float | None:
        return self._current.get("temp", self._first_hour.get("temp"))

    @property
    def native_apparent_temperature(self) -> float | None:
        return None

    @property
    def native_dew_point(self) -> float | None:
        return self._current.get("dewpoint", self._first_hour.get("dewpoint"))

    @property
    def native_pressure(self) -> float | None:
        return self._current.get("pressureMsl", self._first_hour.get("pressureMsl"))

    @property
    def humidity(self) -> float | None:
        return self._current.get(
            "humidityRelative", self._first_hour.get("humidityRelative")
        )

    @property
    def native_wind_speed(self) -> float | None:
        return self._current.get("windSpeed", self._first_hour.get("windSpeed"))

    @property
    def native_wind_gust_speed(self) -> float | None:
        return self._current.get("windGust", self._first_hour.get("windGust"))

    @property
    def wind_bearing(self) -> float | None:
        return self._current.get("windDirection", self._first_hour.get("windDirection"))

    @property
    def cloud_coverage(self) -> float | None:
        return self._current.get("cloudCoverage", self._first_hour.get("cloudCoverage"))

    @property
    def condition(self) -> str | None:
        symbol = self._current.get("weatherSymbol") or self._first_hour.get(
            "weatherSymbol"
        )
        is_day = self._current.get("isDay", self._first_hour.get("isDay"))
        return symbol_to_condition(symbol, is_day)

    @staticmethod
    def _hourly_item(item: dict[str, Any]) -> Forecast:
        return Forecast(
            datetime=item["dateTime"],
            temperature=item.get("temp"),
            precipitation=item.get("precCurrent"),
            wind_speed=item.get("windSpeed"),
            wind_gust_speed=item.get("windGust"),
            wind_bearing=item.get("windDirection"),
            humidity=item.get("humidityRelative"),
            pressure=item.get("pressureMsl"),
            cloud_coverage=item.get("cloudCoverage"),
            condition=symbol_to_condition(item.get("weatherSymbol"), item.get("isDay")),
        )

    @staticmethod
    def _daily_item(item: dict[str, Any]) -> Forecast | None:
        day = dt_util.parse_date(str(item.get("dateTime", ""))[:10])
        if day is None:
            return None
        return Forecast(
            datetime=dt_util.start_of_local_day(day).isoformat(),
            temperature=item.get("tempMax"),
            templow=item.get("tempMin"),
            precipitation=item.get("prec"),
            precipitation_probability=item.get("precProb1mm"),
            wind_gust_speed=item.get("windGust"),
            # Tagesvorhersage: immer Tag-Symbol, kein "clear-night"
            condition=symbol_to_condition(item.get("weatherSymbol"), True),
        )

    def _async_forecast_hourly(self) -> list[Forecast] | None:
        hourly = self.coordinator.data.get("hourly", [])
        return [self._hourly_item(i) for i in hourly if "dateTime" in i] or None

    def _async_forecast_daily(self) -> list[Forecast] | None:
        items = (self._daily_item(i) for i in self.coordinator.data.get("daily", []))
        return [i for i in items if i is not None] or None
