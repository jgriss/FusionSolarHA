from datetime import timedelta
import logging

import async_timeout
from fusion_solar_py.client import FusionSolarClient
from fusion_solar_py.exceptions import AuthenticationException, FusionSolarException

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .id_generator import create_id_hash

_LOGGER = logging.getLogger(__name__)


class FusionSolarCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass, my_api: FusionSolarClient):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="FusionSolarAPI",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(minutes=4),
        )
        self.my_api = my_api
        self.plant_ids = None
        self._update_failure_counter = 0

    def _reset_client(self) -> None:
        """Resets the FusionSolarClient
        """
        new_client = FusionSolarClient(self.my_api._user, self.my_api._password, huawei_subdomain=self.my_api._huawei_subdomain)

        # remove the current one
        self.my_api.log_out()

        self.my_api = new_client

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(60):
                # get the plant ids
                if not self.plant_ids:
                    self.plant_ids = await self.hass.async_add_executor_job(
                        self.my_api.get_plant_ids
                    )

                # overall power status
                power_status = await self.hass.async_add_executor_job(
                    self.my_api.get_power_status
                )

                _LOGGER.debug(f"Got power status: {power_status.current_power_kw}")

                # initialize the data
                data = {
                    "total": {
                        "current_power_kw": power_status.current_power_kw,
                        "power_today_kwh": power_status.total_power_today_kwh,
                    },
                    "plants": {},
                }

                # get the plant specific values
                for plant_id in self.plant_ids:
                    plant_status = await self.hass.async_add_executor_job(
                        self.my_api.get_plant_stats, plant_id
                    )

                    plant_data = self.my_api.get_last_plant_data(plant_status)

                    # save the power data
                    data["plants"][plant_id] = plant_data

                # reset the counter if the update worked
                self._update_failure_counter = 0

                return data
        except AuthenticationException as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise ConfigEntryAuthFailed from err
        except Exception as err:
            _LOGGER.error(f"Error communicating with API: {err}")
            _LOGGER.exception(err)

            self._update_failure_counter += 1

            # reset the fusion solar client after 2 attempts
            if self._update_failure_counter >= 2:
                _LOGGER.info("Reached 2 failures. Resetting fusion_solar client")
                await self.hass.async_add_executor_job(self._reset_client)

            raise UpdateFailed(f"Error communicating with API: {err}") from err
