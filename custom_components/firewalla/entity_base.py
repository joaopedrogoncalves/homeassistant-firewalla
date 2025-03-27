"""Base entity classes for Firewalla integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_GID,
    ATTR_LICENSE,
    ATTR_LOCATION,
    ATTR_MODE,
    ATTR_MODEL,
    ATTR_PUBLIC_IP,
    ATTR_RULE_ID,
    ATTR_VERSION,
    DOMAIN,
    ENTITY_RULE,
)

_LOGGER = logging.getLogger(__name__)


class FirewallaBaseEntity(CoordinatorEntity):
    """Base entity class for Firewalla entities."""

    def __init__(self, coordinator, device_data):
        """Initialize the entity.
        
        Args:
            coordinator: The Firewalla data update coordinator
            device_data: Dictionary containing device information
        """
        super().__init__(coordinator)
        self.device_data = device_data
        self.gid = device_data["gid"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.gid)},
            name=device_data["name"],
            manufacturer="Firewalla",
            model=device_data["model"].capitalize(),
            sw_version=device_data["version"],
            configuration_url=f"https://my.firewalla.com/app/box/{self.gid}",
        )

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the extra state attributes of the entity."""
        current_data = self.get_device_data()
        if not current_data:
            return {}
            
        attributes = {
            ATTR_GID: current_data["gid"],
            ATTR_MODEL: current_data["model"],
            ATTR_VERSION: current_data["version"],
            ATTR_MODE: current_data["mode"],
            ATTR_LICENSE: current_data["license"],
        }

        if "publicIP" in current_data:
            attributes[ATTR_PUBLIC_IP] = current_data["publicIP"]
            
        if "location" in current_data:
            attributes[ATTR_LOCATION] = current_data["location"]
            
        return attributes

    def get_device_data(self) -> Optional[Dict[str, Any]]:
        """Get the current device data from coordinator."""
        if not self.coordinator.data or "devices" not in self.coordinator.data:
            return None
            
        for device in self.coordinator.data["devices"]:
            if device["gid"] == self.gid:
                return device
                
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False
            
        return self.get_device_data() is not None


class FirewallaRuleEntity(CoordinatorEntity):
    """Base entity class for Firewalla rule entities."""

    def __init__(self, coordinator, rule, device_data):
        """Initialize the rule entity.
        
        Args:
            coordinator: The Firewalla data update coordinator
            rule: Dictionary containing rule information
            device_data: Dictionary containing device information for the rule
        """
        super().__init__(coordinator)
        self.rule = rule
        self.device_data = device_data
        
        # Get rule ID, falling back to creating one if missing
        if "id" in rule:
            self.rule_id = rule["id"]
        else:
            # Create a synthetic ID based on other rule properties
            rule_type = rule.get("type", "")
            rule_target = rule.get("target", "unknown")
            if isinstance(rule_target, dict):
                target_value = rule_target.get("value", "unknown")
            else:
                target_value = str(rule_target)
            self.rule_id = f"rule_{rule_type}_{target_value}".replace(" ", "_").lower()
            _LOGGER.warning("Rule missing ID, created synthetic ID: %s", self.rule_id)
            rule["id"] = self.rule_id
            
        # Get device GID, using the one from device_info if missing in rule
        if "gid" in rule:
            self.device_gid = rule["gid"]
        else:
            self.device_gid = device_data.get("gid", "unknown")
            rule["gid"] = self.device_gid
            _LOGGER.warning("Rule missing GID, using device GID: %s", self.device_gid)
            
        # Create a unique ID based on the rule ID itself
        # Replace hyphens with underscores for entity ID compatibility
        safe_rule_id = self.rule_id.replace("-", "_")
        self._attr_unique_id = f"{self.device_gid}_{ENTITY_RULE}_{safe_rule_id}"
        
        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.device_gid)},
            name=device_data.get("name", "Firewalla"),
            manufacturer="Firewalla",
            model=device_data.get("model", "").capitalize(),
            sw_version=device_data.get("version", ""),
            configuration_url=f"https://my.firewalla.com/app/box/{self.device_gid}",
        )
    
    def get_rule_data(self) -> Optional[Dict[str, Any]]:
        """Get the current rule data from coordinator."""
        if not self.coordinator.data or "rules" not in self.coordinator.data:
            return None
            
        for rule in self.coordinator.data["rules"]:
            if isinstance(rule, dict) and rule.get("id") == self.rule_id:
                return rule
                
        return None
    
    def get_device_data(self) -> Optional[Dict[str, Any]]:
        """Get the current device data from coordinator."""
        if not self.coordinator.data or "devices" not in self.coordinator.data:
            return None
            
        for device in self.coordinator.data["devices"]:
            if device["gid"] == self.device_gid:
                return device
                
        return None
        
    @property
    def available(self) -> bool:
        """Return if the entity is available."""
        if not self.coordinator.last_update_success:
            return False
            
        # Check if device is still available and online
        device_data = self.get_device_data()
        if not device_data or not device_data.get("online", False):
            return False
            
        # For rules, we consider them available as long as the device is online
        # even if the rule is temporarily not returned by the API
        return True