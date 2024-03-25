"""The FusionSolar integration."""
from __future__ import annotations

import logging

from fusion_solar_py.client import FusionSolarClient
from fusion_solar_py.exceptions import AuthenticationException, FusionSolarException

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import config_validation as cv, entity_platform, service

from .const import COORDINATOR, DOMAIN
from .sensor import FusionSolarSensor
from .update_coordinator import FusionSolarCoordinator

_LOGGER = logging.getLogger(__name__)


# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up FusionSolar from a config entry."""
    # Store an API object for your platforms to access
    _LOGGER.debug("Creating FusionSolarClient")

    # TODO: catch connection exceptions
    try:
        fusion_client = await hass.async_add_executor_job(
            FusionSolarClient, entry.data["username"], entry.data["password"], entry.data["huawei_subdomain"]
        )
    except AuthenticationException as error:
        raise ConfigEntryAuthFailed from error

    # create the update coordinator
    coordinator = FusionSolarCoordinator(hass, fusion_client)

    # store the coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {COORDINATOR: coordinator}

    # get the initial data
    await coordinator.async_config_entry_first_refresh()

    # create the entities
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
