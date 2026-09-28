"""Kachelmannwetter-Integration für Home Assistant."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import KachelmannApi
from .const import (
    CONF_API_KEY,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .coordinator import KachelmannCoordinator

PLATFORMS: list[Platform] = [Platform.WEATHER, Platform.SENSOR]

KachelmannConfigEntry = ConfigEntry[KachelmannCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: KachelmannConfigEntry) -> bool:
    """Integration aus einem Config-Eintrag einrichten."""
    api = KachelmannApi(async_get_clientsession(hass), entry.data[CONF_API_KEY])
    interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    coordinator = KachelmannCoordinator(
        hass,
        api,
        entry.data[CONF_LATITUDE],
        entry.data[CONF_LONGITUDE],
        interval,
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_options))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_reload_on_options(
    hass: HomeAssistant, entry: KachelmannConfigEntry
) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: KachelmannConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
