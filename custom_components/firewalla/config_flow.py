"""Config flow for Firewalla integration."""
import logging
from typing import Any, Dict, Optional

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_NAME,
)
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class FirewallaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Firewalla."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            api_key = user_input[CONF_API_KEY]

            session = async_get_clientsession(self.hass)
            
            try:
                # Test connection
                url = f"https://{host}/v2/boxes"
                headers = {"Authorization": f"Token {api_key}"}
                
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        _LOGGER.error(
                            "Error connecting to Firewalla: %s - %s",
                            response.status,
                            await response.text(),
                        )
                        errors["base"] = "cannot_connect"
                    else:
                        devices = await response.json()
                        if not devices:
                            errors["base"] = "no_devices_found"
                        else:
                            # Add a unique ID using the Firewalla device ID (GID)
                            await self.async_set_unique_id(devices[0]["gid"])
                            self._abort_if_unique_id_configured()
                            
                            title = f"Firewalla {devices[0]['model'].capitalize()}"
                            
                            return self.async_create_entry(
                                title=title,
                                data={
                                    CONF_HOST: host,
                                    CONF_API_KEY: api_key,
                                },
                            )
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_API_KEY): str,
                }
            ),
            errors=errors,
        )
