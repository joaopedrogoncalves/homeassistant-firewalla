"""Utility functions for Firewalla API response parsing."""
import logging
from typing import Any, Dict, List, Optional, Union

_LOGGER = logging.getLogger(__name__)


def parse_devices_response(data: Any) -> List[Dict[str, Any]]:
    """Parse API response for devices into a standardized format.
    
    Args:
        data: The raw response data from the API
        
    Returns:
        A list of device dictionaries
    """
    # Ensure we have a list of dictionaries
    if not isinstance(data, list):
        _LOGGER.error("Expected list of devices but got: %s", type(data))
        return []
        
    return data


def parse_network_devices_response(data: Any) -> List[Dict[str, Any]]:
    """Parse API response for network devices into a standardized format.
    
    Args:
        data: The raw response data from the API
        
    Returns:
        A list of network device dictionaries
    """
    # Log data statistics
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

def parse_rules_response(data: Any) -> List[Dict[str, Any]]:
    """Parse API response for rules into a standardized format.
    
    This utility function handles various response formats from the Firewalla API
    and converts them into a consistent list of rule dictionaries.
    
    Args:
        data: The raw response data from the API
        
    Returns:
        A list of rule dictionaries
    """
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