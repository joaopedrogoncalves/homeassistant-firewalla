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
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import (
    ATTR_GID,
    ATTR_LICENSE,
    ATTR_LOCATION,
    ATTR_MODE,
    ATTR_MODEL,
    ATTR_PUBLIC_IP,
    ATTR_VERSION,
    DOMAIN,
    ENTITY_ALARM_COUNT,
    ENTITY_DEVICE_COUNT,
    ENTITY_RULE_COUNT,
    FIREWALLA_COORDINATOR,
)

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

    async_add_entities(entities)


class FirewallaBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for Firewalla sensors."""

    def __init__(self, coordinator, device_data):
        """Initialize the sensor."""
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
        for device in self.coordinator.data["devices"]:
            if device["gid"] == self.gid:
                current_data = device
                break
        else:
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

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False
            
        for device in self.coordinator.data["devices"]:
            if device["gid"] == self.gid:
                return True
        return False

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
        for device in self.coordinator.data["devices"]:
            if device["gid"] == self.gid:
                return device["deviceCount"]
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
        for device in self.coordinator.data["devices"]:
            if device["gid"] == self.gid:
                return device["ruleCount"]
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
        for device in self.coordinator.data["devices"]:
            if device["gid"] == self.gid:
                return device["alarmCount"]
        return 0
