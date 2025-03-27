"""Firewalla API client."""
import logging
from typing import Any, Dict, List, Optional, Union

import aiohttp

_LOGGER = logging.getLogger(__name__)


class FirewallaAPI:
    """Firewalla API Client."""

    def __init__(self, session: aiohttp.ClientSession, host: str, api_key: str):
        """Initialize the API client.
        
        Args:
            session: The aiohttp client session
            host: The Firewalla host IP or hostname
            api_key: The API key for authentication
        """
        self.session = session
        self.host = host
        self.api_key = api_key
        self.base_url = f"https://{host}"
        self.headers = {"Authorization": f"Token {api_key}"}

    async def get_devices(self) -> List[Dict[str, Any]]:
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
                    return []
                    
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
            
    async def get_network_devices(self, device_gid: Optional[str] = None) -> List[Dict[str, Any]]:
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
                    return []
                    
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
            
    async def get_rules(self, device_gid: Optional[str] = None) -> List[Dict[str, Any]]:
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
                    return []
                    
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
            
    async def pause_rule(self, rule_id: str) -> bool:
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
            
    async def resume_rule(self, rule_id: str) -> bool:
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