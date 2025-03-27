"""Binary sensor platform for Firewalla integration."""
from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ENTITY_ONLINE,
    FIREWALLA_COORDINATOR,
)
from .entity_base import FirewallaBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Firewalla binary sensor entries."""
    coordinator = hass.data[DOMAIN][entry.entry_id][FIREWALLA_COORDINATOR]
    
    if not coordinator.data or "devices" not in coordinator.data:
        _LOGGER.error("No devices data available in coordinator")
        return
    
    entities = []
    
    # Log the data structure for debugging
    _LOGGER.debug("Devices data structure: %s", coordinator.data["devices"])
    
    for device_data in coordinator.data["devices"]:
        # Ensure device_data is a dictionary
        if not isinstance(device_data, dict):
            _LOGGER.error("Unexpected device data format: %s", type(device_data))
            continue
            
        # Add online status binary sensor
        try:
            entities.append(
                FirewallaOnlineSensor(
                    coordinator=coordinator,
                    device_data=device_data,
                )
            )
        except Exception as ex:
            _LOGGER.error("Error creating FirewallaOnlineSensor: %s", ex)

    async_add_entities(entities)


class FirewallaOnlineSensor(FirewallaBaseEntity, BinarySensorEntity):
    """Representation of a Firewalla online status sensor."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    
    def __init__(self, coordinator, device_data):
        """Initialize the sensor."""
        super().__init__(coordinator, device_data)
        self._attr_unique_id = f"{self.gid}_{ENTITY_ONLINE}"
        self._attr_name = f"{device_data['name']} Online"

    @property
    def is_on(self) -> bool:
        """Return true if the Firewalla is online."""
        device_data = self.get_device_data()
        if device_data:
            return device_data.get("online", False)
        return False
