"""
Home Assistant integration for Firewalla devices.
For more information about this integration, please visit:
https://github.com/yourusername/homeassistant-firewalla
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
        try:
            async with self.session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    _LOGGER.error(
                        "Error getting Firewalla devices: %s - %s",
                        response.status,
                        await response.text(),
                    )
                    return None
                    
                data = await response.json()
                _LOGGER.debug("Devices API response: %s", data)
                
                # Ensure we have a list of dictionaries
                if not isinstance(data, list):
                    _LOGGER.error("Expected list of devices but got: %s", type(data))
                    return []
                    
                return data
        except Exception as ex:
            _LOGGER.error("Exception in get_devices: %s", ex)
            return []
            
    async def get_network_devices(self, device_gid=None):
        """Get network devices from Firewalla."""
        url = f"{self.base_url}/v2/devices"
        if device_gid:
            url = f"{url}?gid={device_gid}"
            
        _LOGGER.debug("Fetching network devices from: %s", url)
            
        try:
            async with self.session.get(url, headers=self.headers) as response:
                response_text = await response.text()
                _LOGGER.debug("Network devices response status: %s", response.status)
                
                if response.status != 200:
                    _LOGGER.error(
                        "Error getting network devices: %s - %s",
                        response.status,
                        response_text,
                    )
                    return None
                    
                try:
                    data = await response.json()
                    device_count = len(data) if isinstance(data, list) else "unknown"
                    _LOGGER.debug("Received %s network devices", device_count)
                    
                    # Log a sample of the data if available
                    if isinstance(data, list) and len(data) > 0:
                        _LOGGER.debug("Sample network device: %s", data[0])
                    
                    # Ensure we have a list
                    if not isinstance(data, list):
                        _LOGGER.error("Expected list of network devices but got: %s", type(data))
                        return []
                        
                    return data
                except Exception as ex:
                    _LOGGER.error("Error parsing network devices response: %s - %s", ex, response_text[:200])
                    return []
        except Exception as ex:
            _LOGGER.error("Exception in get_network_devices: %s", ex)
            return []
            
    async def get_rules(self, device_gid=None):
        """Get rules from Firewalla."""
        url = f"{self.base_url}/v2/rules"
        if device_gid:
            url = f"{url}?gid={device_gid}"
            
        try:
            async with self.session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    _LOGGER.error(
                        "Error getting Firewalla rules: %s - %s",
                        response.status,
                        await response.text(),
                    )
                    return None
                    
                data = await response.json()
                _LOGGER.debug("Rules API response for device %s: %s", device_gid, data)
                
                # Log the structure of the data to help debug
                if isinstance(data, dict):
                    _LOGGER.debug("Dictionary keys in rules response: %s", list(data.keys()))
                
                # Handle various formats of responses
                if isinstance(data, dict):
                    # Try to find the rules in the dictionary, checking common keys
                    for key in ["rules", "data", "items", "results"]:
                        if key in data and isinstance(data[key], list):
                            _LOGGER.debug("Found rules under key '%s'", key)
                            return data[key]
                    
                    # If we didn't find a known key but have a single array value, use that
                    for key, value in data.items():
                        if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                            _LOGGER.debug("Using list value from key '%s' as rules", key)
                            return value
                    
                    # If we couldn't find any list to use, convert the dictionary to rules if possible
                    # This handles the case where the dictionary itself represents the rules
                    _LOGGER.debug("Converting dictionary to rule list")
                    result = []
                    for key, value in data.items():
                        if isinstance(value, dict) and "id" in value:
                            # This looks like a rule item
                            result.append(value)
                        elif key.startswith("rule_") and isinstance(value, dict):
                            rule = value.copy()
                            rule["id"] = key
                            result.append(rule)
                    
                    if result:
                        _LOGGER.debug("Converted %d dictionary entries to rules", len(result))
                        return result
                    else:
                        # As a last resort, treat the whole dictionary as a single rule
                        if "id" in data or "target" in data or "action" in data:
                            _LOGGER.debug("Treating whole dictionary as a single rule")
                            # Ensure the rule has an ID
                            if "id" not in data and "gid" in data:
                                rule_copy = data.copy()
                                rule_copy["id"] = f"rule_{data['gid']}"
                                return [rule_copy]
                            return [data]
                        
                    _LOGGER.error("Could not extract rules from dictionary: %s", data)
                    return []
                elif isinstance(data, list):
                    # If it's already a list, use it directly
                    return data
                else:
                    _LOGGER.error("Unexpected rules data format: %s", type(data))
                    return []
        except Exception as ex:
            _LOGGER.error("Exception in get_rules: %s", ex)
            return []
            
    async def pause_rule(self, rule_id):
        """Pause a rule."""
        url = f"{self.base_url}/v2/rules/{rule_id}/pause"
        try:
            async with self.session.post(url, headers=self.headers) as response:
                response_text = await response.text()
                _LOGGER.debug("Pause rule response: %s - %s", response.status, response_text)
                
                if response.status != 200:
                    _LOGGER.error(
                        "Error pausing rule: %s - %s",
                        response.status,
                        response_text,
                    )
                    return False
                    
                # Try to parse the response
                try:
                    data = await response.json()
                    _LOGGER.debug("Pause rule response data: %s", data)
                    return True
                except:
                    # If we can't parse JSON but got a 200, consider it success
                    return True
        except Exception as ex:
            _LOGGER.error("Exception in pause_rule: %s", ex)
            return False
            
    async def resume_rule(self, rule_id):
        """Resume a rule."""
        url = f"{self.base_url}/v2/rules/{rule_id}/resume"
        try:
            async with self.session.post(url, headers=self.headers) as response:
                response_text = await response.text()
                _LOGGER.debug("Resume rule response: %s - %s", response.status, response_text)
                
                if response.status != 200:
                    _LOGGER.error(
                        "Error resuming rule: %s - %s",
                        response.status,
                        response_text,
                    )
                    return False
                    
                # Try to parse the response
                try:
                    data = await response.json()
                    _LOGGER.debug("Resume rule response data: %s", data)
                    return True
                except:
                    # If we can't parse JSON but got a 200, consider it success
                    return True
        except Exception as ex:
            _LOGGER.error("Exception in resume_rule: %s", ex)
            return False


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
        self.network_devices = []
        self.device_groups = {}  # Map group IDs to group names

    async def _async_update_data(self):
        """Fetch data from Firewalla."""
        try:
            # Get devices
            devices = await self.api.get_devices()
            if not devices:
                raise UpdateFailed("Failed to fetch Firewalla devices")
                
            # Ensure devices is a list of dictionaries
            if isinstance(devices, str):
                _LOGGER.error("Received unexpected string response for devices: %s", devices)
                raise UpdateFailed("Unexpected response format from API")
                
            self.devices = devices
            
            # Get network devices
            all_network_devices = []
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
            
            _LOGGER.debug("Found device groups: %s", self.device_groups)
            
            # Get rules for all devices
            all_rules = []
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
            
            return {
                "devices": devices,
                "rules": all_rules,
                "network_devices": all_network_devices,
                "device_groups": self.device_groups
            }
        except Exception as ex:
            _LOGGER.error("Error updating Firewalla data: %s", ex)
            raise UpdateFailed(f"Error communicating with Firewalla API: {ex}") from ex
