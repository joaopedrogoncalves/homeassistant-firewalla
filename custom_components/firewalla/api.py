"""Firewalla API client."""
import logging
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import aiohttp

from .api_utils import (
    parse_devices_response,
    parse_network_devices_response,
    parse_rules_response,
)
from .logger import log_api_error, log_exception

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
        endpoint = "/v2/boxes"
        url = f"{self.base_url}{endpoint}"
        try:
            async with self.session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    response_text = await response.text()
                    log_api_error(_LOGGER, endpoint, response.status, response_text)
                    return []
                    
                data = await response.json()
                _LOGGER.debug("Devices API response received")
                
                return parse_devices_response(data)
        except Exception as ex:
            log_exception(_LOGGER, "Failed to get Firewalla devices", ex)
            return []
            
    async def get_network_devices(self, device_gid: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get network devices from Firewalla."""
        endpoint = "/v2/devices"
        url = f"{self.base_url}{endpoint}"
        if device_gid:
            url = f"{url}?gid={device_gid}"
            
        _LOGGER.debug("Fetching network devices from: %s", url)
            
        try:
            async with self.session.get(url, headers=self.headers) as response:
                response_text = await response.text()
                _LOGGER.debug("Network devices response status: %s", response.status)
                
                if response.status != 200:
                    log_api_error(_LOGGER, endpoint, response.status, response_text)
                    return []
                    
                try:
                    data = await response.json()
                    return parse_network_devices_response(data)
                except Exception as ex:
                    log_exception(
                        _LOGGER, 
                        "Error parsing network devices response", 
                        ex, 
                        logging.ERROR
                    )
                    return []
        except Exception as ex:
            log_exception(_LOGGER, "Failed to get network devices", ex)
            return []
            
    async def get_rules(self, device_gid: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get rules from Firewalla."""
        endpoint = "/v2/rules"
        url = f"{self.base_url}{endpoint}"
        if device_gid:
            url = f"{url}?gid={device_gid}"
            
        try:
            async with self.session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    response_text = await response.text()
                    log_api_error(_LOGGER, endpoint, response.status, response_text)
                    return []
                    
                data = await response.json()
                _LOGGER.debug("Rules API response for device %s", device_gid)
                
                # Use the utility function to parse the rules response
                return parse_rules_response(data)
        except Exception as ex:
            log_exception(_LOGGER, "Failed to get rules", ex)
            return []
            
    async def pause_rule(self, rule_id: str) -> bool:
        """Pause a rule."""
        endpoint = f"/v2/rules/{rule_id}/pause"
        url = f"{self.base_url}{endpoint}"
        try:
            async with self.session.post(url, headers=self.headers) as response:
                response_text = await response.text()
                _LOGGER.debug("Pause rule response: %s - %s", response.status, response_text)
                
                if response.status != 200:
                    log_api_error(_LOGGER, endpoint, response.status, response_text)
                    return False
                    
                # Try to parse the response
                try:
                    data = await response.json()
                    _LOGGER.debug("Pause rule response data: %s", data)
                    return True
                except Exception as json_ex:
                    # If we can't parse JSON but got a 200, consider it success
                    _LOGGER.debug("Could not parse JSON response for pause rule, but got 200 status")
                    return True
        except Exception as ex:
            log_exception(_LOGGER, f"Failed to pause rule {rule_id}", ex)
            return False
            
    async def resume_rule(self, rule_id: str) -> bool:
        """Resume a rule."""
        endpoint = f"/v2/rules/{rule_id}/resume"
        url = f"{self.base_url}{endpoint}"
        try:
            async with self.session.post(url, headers=self.headers) as response:
                response_text = await response.text()
                _LOGGER.debug("Resume rule response: %s - %s", response.status, response_text)
                
                if response.status != 200:
                    log_api_error(_LOGGER, endpoint, response.status, response_text)
                    return False
                    
                # Try to parse the response
                try:
                    data = await response.json()
                    _LOGGER.debug("Resume rule response data: %s", data)
                    return True
                except Exception as json_ex:
                    # If we can't parse JSON but got a 200, consider it success
                    _LOGGER.debug("Could not parse JSON response for resume rule, but got 200 status")
                    return True
        except Exception as ex:
            log_exception(_LOGGER, f"Failed to resume rule {rule_id}", ex)
            return False