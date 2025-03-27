"""Sensor platform for Firewalla integration."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ENTITY_ALARM_COUNT,
    ENTITY_DEVICE_COUNT,
    ENTITY_RULE_COUNT,
    FIREWALLA_COORDINATOR,
)
from .entity_base import FirewallaBaseEntity

# Remove this import since we'll handle network devices differently
# from .network_device_sensor import async_setup_network_device_sensors

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Firewalla sensor entries."""
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
            
        try:
            # Add device count sensor
            entities.append(
                FirewallaDeviceCountSensor(
                    coordinator=coordinator,
                    device_data=device_data,
                )
            )
            
            # Add rule count sensor
            entities.append(
                FirewallaRuleCountSensor(
                    coordinator=coordinator,
                    device_data=device_data,
                )
            )
            
            # Add alarm count sensor
            entities.append(
                FirewallaAlarmCountSensor(
                    coordinator=coordinator,
                    device_data=device_data,
                )
            )
        except Exception as ex:
            _LOGGER.error("Error creating sensor for device %s: %s", 
                         device_data.get("name", "unknown"), ex)

    _LOGGER.info("Adding %d firewalla sensor entities", len(entities))
    async_add_entities(entities)
    
    # We'll add network device sensor support once the main functionality is working reliably
    # This can be re-enabled in a future update



class FirewallaBaseSensor(FirewallaBaseEntity, SensorEntity):
    """Base class for Firewalla sensors."""

    async def async_update(self) -> None:
        """Update the sensor."""
        await self.coordinator.async_request_refresh()


class FirewallaDeviceCountSensor(FirewallaBaseSensor):
    """Representation of a Firewalla device count sensor."""

    _attr_native_unit_of_measurement = "devices"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:devices"

    def __init__(self, coordinator, device_data):
        """Initialize the sensor."""
        super().__init__(coordinator, device_data)
        self._attr_unique_id = f"{self.gid}_{ENTITY_DEVICE_COUNT}"
        self._attr_name = f"{device_data['name']} Device Count"

    @property
    def native_value(self) -> int:
        """Return the device count."""
        device_data = self.get_device_data()
        if device_data:
            return device_data.get("deviceCount", 0)
        return 0


class FirewallaRuleCountSensor(FirewallaBaseSensor):
    """Representation of a Firewalla rule count sensor."""

    _attr_native_unit_of_measurement = "rules"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:shield"

    def __init__(self, coordinator, device_data):
        """Initialize the sensor."""
        super().__init__(coordinator, device_data)
        self._attr_unique_id = f"{self.gid}_{ENTITY_RULE_COUNT}"
        self._attr_name = f"{device_data['name']} Rule Count"

    @property
    def native_value(self) -> int:
        """Return the rule count."""
        device_data = self.get_device_data()
        if device_data:
            return device_data.get("ruleCount", 0)
        return 0


class FirewallaAlarmCountSensor(FirewallaBaseSensor):
    """Representation of a Firewalla alarm count sensor."""

    _attr_native_unit_of_measurement = "alarms"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:alarm-light"

    def __init__(self, coordinator, device_data):
        """Initialize the sensor."""
        super().__init__(coordinator, device_data)
        self._attr_unique_id = f"{self.gid}_{ENTITY_ALARM_COUNT}"
        self._attr_name = f"{device_data['name']} Alarm Count"

    @property
    def native_value(self) -> int:
        """Return the alarm count."""
        device_data = self.get_device_data()
        if device_data:
            return device_data.get("alarmCount", 0)
        return 0
