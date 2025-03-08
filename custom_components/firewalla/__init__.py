"""
Home Assistant integration for Firewalla devices.
For more information about this integration, please visit:
https://github.com/joaopedrogoncalves/homeassistant-firewalla
"""
import logging
import asyncio
from datetime import timedelta
import voluptuous as vol

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_NAME,
    Platform,
)
from homeassistant.exceptions import ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, FIREWALLA_COORDINATOR, SERVICE_PAUSE_RULE, SERVICE_RESUME_RULE

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=1)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Required(CONF_API_KEY): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Firewalla component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Firewalla from a config entry."""
    host = entry.data[CONF_HOST]
    api_key = entry.data[CONF_API_KEY]

    session = async_get_clientsession(hass)
    api = FirewallaAPI(session, host, api_key)

    # Test API connection
    try:
        devices = await api.get_devices()
        if not devices:
            raise ConfigEntryNotReady("No Firewalla devices found")
    except Exception as ex:
        raise ConfigEntryNotReady(f"Cannot connect to Firewalla API: {ex}") from ex

    coordinator = FirewallaDataUpdateCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        FIREWALLA_COORDINATOR: coordinator,
    }

    # Register services
    async def pause_rule(call):
        """Pause a rule."""
        rule_id = call.data.get("rule_id")
        if not rule_id:
            _LOGGER.error("No rule_id provided to pause_rule service")
            return
        
        await api.pause_rule(rule_id)
        await coordinator.async_request_refresh()
    
    async def resume_rule(call):
        """Resume a rule."""
        rule_id = call.data.get("rule_id")
        if not rule_id:
            _LOGGER.error("No rule_id provided to resume_rule service")
            return
        
        await api.resume_rule(rule_id)
        await coordinator.async_request_refresh()
    
    # Register the services
    hass.services.async_register(
        DOMAIN, SERVICE_PAUSE_RULE, pause_rule, vol.Schema({vol.Required("rule_id"): cv.string})
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_RESUME_RULE, resume_rule, vol.Schema({vol.Required("rule_id"): cv.string})
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class FirewallaAPI:
    """Firewalla API Client."""

    def __init__(self, session, host, api_key):
        """Initialize the API client."""
        self.session = session
        self.host = host
        self.api_key = api_key
        self.base_url = f"https://{host}"
        self.headers = {"Authorization": f"Token {api_key}"}

    async def get_devices(self):
        """Get Firewalla devices."""
        url = f"{self.base_url}/v2/boxes"
        async with self.session.get(url, headers=self.headers) as response:
            if response.status != 200:
                _LOGGER.error(
                    "Error getting Firewalla devices: %s - %s",
                    response.status,
                    await response.text(),
                )
                return None
            return await response.json()
            
    async def get_rules(self, device_gid=None):
        """Get rules from Firewalla."""
        url = f"{self.base_url}/v2/rules"
        if device_gid:
            url = f"{url}?gid={device_gid}"
            
        async with self.session.get(url, headers=self.headers) as response:
            if response.status != 200:
                _LOGGER.error(
                    "Error getting Firewalla rules: %s - %s",
                    response.status,
                    await response.text(),
                )
                return None
            return await response.json()
            
    async def pause_rule(self, rule_id):
        """Pause a rule."""
        url = f"{self.base_url}/v2/rules/{rule_id}/pause"
        async with self.session.post(url, headers=self.headers) as response:
            if response.status != 200:
                _LOGGER.error(
                    "Error pausing rule: %s - %s",
                    response.status,
                    await response.text(),
                )
                return False
            return True
            
    async def resume_rule(self, rule_id):
        """Resume a rule."""
        url = f"{self.base_url}/v2/rules/{rule_id}/resume"
        async with self.session.post(url, headers=self.headers) as response:
            if response.status != 200:
                _LOGGER.error(
                    "Error resuming rule: %s - %s",
                    response.status,
                    await response.text(),
                )
                return False
            return True


class FirewallaDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Firewalla data."""

    def __init__(self, hass: HomeAssistant, api: FirewallaAPI):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.api = api
        self.devices = []
        self.rules = []

    async def _async_update_data(self):
        """Fetch data from Firewalla."""
        try:
            # Get devices
            devices = await self.api.get_devices()
            if not devices:
                raise UpdateFailed("Failed to fetch Firewalla devices")
                
            self.devices = devices
            
            # Get rules for all devices
            rules = []
            for device in devices:
                device_rules = await self.api.get_rules(device["gid"])
                if device_rules:
                    rules.extend(device_rules)
            
            self.rules = rules
            
            return {
                "devices": devices,
                "rules": rules
            }
        except Exception as ex:
            _LOGGER.error("Error updating Firewalla data: %s", ex)
            raise UpdateFailed(f"Error communicating with Firewalla API: {ex}") from ex
