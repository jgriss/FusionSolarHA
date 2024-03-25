"""Config flow for FusionSolar integration."""
from __future__ import annotations

import logging
from typing import Any

from fusion_solar_py.client import FusionSolarClient
from fusion_solar_py.exceptions import AuthenticationException, FusionSolarException
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
        vol.Optional("huawei_subdomain", default="region03eu5"): str
    }
)


class FusionSolar:
    """Integration of the FusionSolarAPI"""

    def __init__(self) -> None:
        """Initialize."""
        self.client = None

    async def authenticate(self, username: str, password: str, huawei_subdomain: str) -> bool:
        """Test if we can authenticate with the host."""

        try:
            if self.client:
                self.client.log_out()

            self.client = FusionSolarClient(username, password, huawei_subdomain)

        except AuthenticationException as error:
            _LOGGER.warning(
                "Wrong username or password for the FusionSolar API: %s", str(error)
            )
            return False
        except FusionSolarException as error:
            _LOGGER.error(
                "Failed to authenticate with the FusionSolar API: %s", str(error)
            )
            raise error

        return True


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    try:
        # only creating the client already attempts a login
        await hass.async_add_executor_job(
            FusionSolarClient, data["username"], data["password"], data["huawei_subdomain"]
        )
    except AuthenticationException as error:
        raise InvalidAuth from error
    except FusionSolarException as error:
        raise CannotConnect from error

    # Return info that you want to store in the config entry.
    return {"title": "FusionSolar"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FusionSolar."""

    VERSION = 1
    MINOR_VERSION = 2

    async def _async_do_task(self, task):
        await task  # A task that take some time to complete.

        # Continue the flow after show progress when the task is done.
        # To avoid a potential deadlock we create a new task that continues the flow.
        # The task must be completely done so the flow can await the task
        # if needed and get the task result.
        self.hass.async_create_task(
            self.hass.config_entries.flow.async_configure(flow_id=self.flow_id)
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        # set the unique id and abort if it is already set
        await self.async_set_unique_id(user_input["username"])
        self._abort_if_unique_id_configured()

        # create a task to validate the user input
        errors = {}

        try:
            info = await validate_input(self.hass, user_input)

            return self.async_create_entry(title=info["title"], data=user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
