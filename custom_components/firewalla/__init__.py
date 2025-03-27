"""
Home Assistant integration for Firewalla devices.
For more information about this integration, please visit:
https://github.com/yourusername/homeassistant-firewalla
"""
from __future__ import annotations

import logging
import asyncio
from datetime import timedelta
from typing import Any, Dict, List, Mapping, Optional

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
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

from .api import FirewallaAPI
from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FIREWALLA_COORDINATOR,
    SERVICE_PAUSE_RULE,
    SERVICE_RESUME_RULE,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

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


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Firewalla component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
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
    register_services(hass, api, coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


def register_services(
    hass: HomeAssistant, 
    api: FirewallaAPI, 
    coordinator: FirewallaDataUpdateCoordinator
) -> None:
    """Register integration services."""
    
    async def pause_rule(call: ServiceCall) -> None:
        """Pause a rule."""
        rule_id = call.data.get("rule_id")
        if not rule_id:
            _LOGGER.error("No rule_id provided to pause_rule service")
            return
        
        await api.pause_rule(rule_id)
        await coordinator.async_request_refresh()
    
    async def resume_rule(call: ServiceCall) -> None:
        """Resume a rule."""
        rule_id = call.data.get("rule_id")
        if not rule_id:
            _LOGGER.error("No rule_id provided to resume_rule service")
            return
        
        await api.resume_rule(rule_id)
        await coordinator.async_request_refresh()
    
    # Register the services
    hass.services.async_register(
        DOMAIN, 
        SERVICE_PAUSE_RULE, 
        pause_rule, 
        vol.Schema({vol.Required("rule_id"): cv.string})
    )
    
    hass.services.async_register(
        DOMAIN, 
        SERVICE_RESUME_RULE, 
        resume_rule, 
        vol.Schema({vol.Required("rule_id"): cv.string})
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class FirewallaDataUpdateCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Class to manage fetching Firewalla data."""

    def __init__(self, hass: HomeAssistant, api: FirewallaAPI) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.api = api
        self.devices: List[Dict[str, Any]] = []
        self.rules: List[Dict[str, Any]] = []
        self.network_devices: List[Dict[str, Any]] = []
        self.device_groups: Dict[str, str] = {}  # Map group IDs to group names

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Firewalla."""
        try:
            # Get devices first - this is critical for all other functionality
            devices = await self.api.get_devices()
            if not devices:
                raise UpdateFailed("Failed to fetch Firewalla devices")
                
            # Ensure devices is a list of dictionaries
            if isinstance(devices, str):
                _LOGGER.error("Received unexpected string response for devices: %s", devices)
                raise UpdateFailed("Unexpected response format from API")
                
            self.devices = devices
            
            # Get rules for all devices - this is critical for rule switches
            all_rules: List[Dict[str, Any]] = []
            for device in devices:
                device_gid = device.get("gid")
                if not device_gid:
                    continue
                    
                device_rules = await self.api.get_rules(device_gid)
                if device_rules:
                    # Ensure rules is a list of dictionaries
                    if isinstance(device_rules, list):
                        all_rules.extend(device_rules)
                    else:
                        _LOGGER.error("Received unexpected format for rules: %s", type(device_rules))
            
            self.rules = all_rules
            
            # Initial data structure with critical components
            result: Dict[str, Any] = {
                "devices": devices,
                "rules": all_rules,
            }
            
            # Try to get network devices, but don't fail if this part doesn't work
            # For now we're just collecting the data, but not creating entities from it
            try:
                all_network_devices: List[Dict[str, Any]] = []
                for device in devices:
                    device_gid = device.get("gid")
                    if not device_gid:
                        continue
                        
                    network_devices = await self.api.get_network_devices(device_gid)
                    if network_devices:
                        all_network_devices.extend(network_devices)
                
                self.network_devices = all_network_devices
                
                # Build a map of group IDs to group names
                self.device_groups = {}
                for device in all_network_devices:
                    if "group" in device and isinstance(device["group"], dict):
                        group_id = device["group"].get("id")
                        group_name = device["group"].get("name")
                        if group_id and group_name:
                            self.device_groups[group_id] = group_name
                
                # Add network device data to result if available - just for data collection
                # We're not creating entities from this data yet
                result["network_devices"] = all_network_devices
                result["device_groups"] = self.device_groups
                
                _LOGGER.debug("Successfully retrieved network devices: %d devices, %d groups", 
                             len(all_network_devices), len(self.device_groups))
            except Exception as ex:
                _LOGGER.warning("Error retrieving network devices, continuing without them: %s", ex)
                # Don't re-raise - we want to continue even if network devices fail
            
            return result
        except Exception as ex:
            _LOGGER.error("Error updating Firewalla data: %s", ex)
            raise UpdateFailed(f"Error communicating with Firewalla API: {ex}") from ex
