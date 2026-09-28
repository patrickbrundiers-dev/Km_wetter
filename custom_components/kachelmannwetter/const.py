"""Konstanten für die Kachelmannwetter-Integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "kachelmannwetter"

API_BASE_URL = "https://api.kachelmannwetter.com/v02"
API_TIMEOUT = 15

CONF_API_KEY = "api_key"
CONF_UPDATE_INTERVAL = "update_interval"

# Hobby-Tarif: 700 Requests/Tag. Pro Update werden 2 Requests gesendet
# (aktuell + stündlich), der 14-Tage-Trend nur alle TREND_REFRESH.
# Bei 15 Minuten: 96 * 2 + 8 = ca. 200 Requests/Tag pro Standort.
DEFAULT_UPDATE_INTERVAL = 15  # Minuten
MIN_UPDATE_INTERVAL = 5
MAX_UPDATE_INTERVAL = 120
TREND_REFRESH = timedelta(hours=3)

# Kachelmann weatherSymbol -> Home-Assistant-Zustand
SYMBOL_TO_CONDITION: dict[str, str] = {
    "sunshine": "sunny",
    "partlycloudy": "partlycloudy",
    "partlycloudy2": "partlycloudy",
    "cloudy": "cloudy",
    "overcast": "cloudy",
    "fog": "fog",
    "rain": "rainy",
    "raindrizzle": "rainy",
    "showers": "rainy",
    "showers_moderate": "rainy",
    "showers_rain_light": "rainy",
    "rainheavy": "pouring",
    "showersheavy": "pouring",
    "thunderstorm": "lightning-rainy",
    "severethunderstorm": "lightning-rainy",
    "snow": "snowy",
    "snowheavy": "snowy",
    "snowshowers": "snowy",
    "snowshowersheavy": "snowy",
    "snowrain": "snowy-rainy",
    "snowrainshowers": "snowy-rainy",
    "freezingrain": "snowy-rainy",
    "wind": "windy",
}
