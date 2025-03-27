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
    ATTR_VERSION,
    DOMAIN,
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