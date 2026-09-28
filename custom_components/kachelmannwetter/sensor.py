"""Sensoren: aktuelle Zusatzwerte und Regenvorhersage."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfLength,
    UnitOfPrecipitationDepth,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import KachelmannConfigEntry
from .coordinator import KachelmannCoordinator
from .weather import device_info

RAIN_THRESHOLD_MM = 0.1


def _current(data: dict[str, Any], *keys: str) -> Any:
    cur = data.get("current", {})
    for key in keys:
        if cur.get(key) is not None:
            return cur[key]
    return None


def _sum_next(data: dict[str, Any], hours: int) -> float | None:
    values = [
        h.get("precCurrent")
        for h in data.get("hourly", [])[:hours]
        if h.get("precCurrent") is not None
    ]
    return round(sum(values), 1) if values else None


def _next_rain(data: dict[str, Any]) -> datetime | None:
    for hour in data.get("hourly", []):
        amount = hour.get("precCurrent")
        if amount is not None and amount >= RAIN_THRESHOLD_MM:
            return dt_util.parse_datetime(hour["dateTime"])
    return None


def _prob_today(data: dict[str, Any]) -> float | None:
    daily = data.get("daily", [])
    return daily[0].get("precProb1mm") if daily else None


def _snow_cm(data: dict[str, Any]) -> float | None:
    value = _current(data, "snowHeight")
    return round(value * 100, 1) if value is not None else None


@dataclass(frozen=True, kw_only=True)
class KachelmannSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]


SENSORS: tuple[KachelmannSensorDescription, ...] = (
    KachelmannSensorDescription(
        key="dew_point",
        translation_key="dew_point",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _current(d, "dewpoint"),
    ),
    KachelmannSensorDescription(
        key="wind_gust",
        translation_key="wind_gust",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        suggested_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _current(d, "windGust"),
    ),
    KachelmannSensorDescription(
        key="cloud_coverage",
        translation_key="cloud_coverage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:cloud",
        value_fn=lambda d: _current(d, "cloudCoverage"),
    ),
    KachelmannSensorDescription(
        key="precipitation_1h",
        translation_key="precipitation_1h",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _current(d, "prec1h", "precCurrent"),
    ),
    KachelmannSensorDescription(
        key="snow_height",
        translation_key="snow_height",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_snow_cm,
    ),
    KachelmannSensorDescription(
        key="precipitation_next_3h",
        translation_key="precipitation_next_3h",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        value_fn=lambda d: _sum_next(d, 3),
    ),
    KachelmannSensorDescription(
        key="precipitation_next_24h",
        translation_key="precipitation_next_24h",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        value_fn=lambda d: _sum_next(d, 24),
    ),
    KachelmannSensorDescription(
        key="next_rain",
        translation_key="next_rain",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_next_rain,
    ),
    KachelmannSensorDescription(
        key="precipitation_probability_today",
        translation_key="precipitation_probability_today",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:weather-rainy",
        value_fn=_prob_today,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KachelmannConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        KachelmannSensor(coordinator, entry, description) for description in SENSORS
    )


class KachelmannSensor(CoordinatorEntity[KachelmannCoordinator], SensorEntity):
    entity_description: KachelmannSensorDescription
    _attr_has_entity_name = True
    _attr_attribution = "Wetterdaten von Meteologix AG / Kachelmann Gruppe"

    def __init__(
        self,
        coordinator: KachelmannCoordinator,
        entry: KachelmannConfigEntry,
        description: KachelmannSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = device_info(entry)

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)
