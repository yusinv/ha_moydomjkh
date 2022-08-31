"""Adds config flow for moydomjkh integration."""
from __future__ import annotations

from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from moydomjkh import Session

from .const import DOMAIN

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string

    }
)


class MoyDomJKHConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for moydomjkh integration."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input:

            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            valid = await self.async_validate_credentials(username, password)

            if not valid:
                errors["base"] = "invalid_credentials"
            else:
                await self.async_set_unique_id(username)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f'moydomjkh_{username}',
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password
                    }
                )

            return self.async_show_form(
                step_id="user",
                data_schema=DATA_SCHEMA,
                errors=errors,
            )

        else:
            return self.async_show_form(
                step_id="user",
                data_schema=DATA_SCHEMA
            )

    async def async_validate_credentials(self, username: str, password: str) -> bool:
        """Validate credentials."""

        def check() -> bool:
            return Session(username, password).check_credentials()

        result = await self.hass.async_add_executor_job(check)
        return result
