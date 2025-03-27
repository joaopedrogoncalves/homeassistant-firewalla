"""Firewalla API client."""
import logging
from typing import Any, Dict, List, Optional, Union

import aiohttp

from .api_utils import (
    parse_devices_response,
    parse_network_devices_response,
    parse_rules_response,
)

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
                _LOGGER.debug("Devices API response received")
                
                return parse_devices_response(data)
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
                    return parse_network_devices_response(data)
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
                _LOGGER.debug("Rules API response for device %s", device_gid)
                
                # Use the utility function to parse the rules response
                return parse_rules_response(data)
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