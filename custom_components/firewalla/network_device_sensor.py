"""Sensor platform for Firewalla network devices."""
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
from homeassistant.const import (
    UnitOfDataRate,
    UnitOfInformation,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import (
    DOMAIN,
    FIREWALLA_COORDINATOR,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Firewalla network device sensors."""
    _LOGGER.debug("Setting up network device sensors directly")
    
    coordinator = hass.data[DOMAIN][entry.entry_id][FIREWALLA_COORDINATOR]
    
    if not coordinator.data or "network_devices" not in coordinator.data:
        _LOGGER.warning("No network device data available yet")
        return
    
    _LOGGER.debug("Found %d network devices", 
                 len(coordinator.data["network_devices"]) if isinstance(coordinator.data["network_devices"], list) else 0)
    
    entities = []
    
    # Create a mapping of device GIDs to device info
    firewalla_devices = {}
    if "devices" in coordinator.data:
        for device in coordinator.data["devices"]:
            if isinstance(device, dict) and "gid" in device:
                firewalla_devices[device["gid"]] = device
    
    # Create sensors for each network device
    for device in coordinator.data["network_devices"]:
        # Ensure device data is a dictionary
        if not isinstance(device, dict):
            _LOGGER.warning("Network device is not a dictionary: %s", type(device))
            continue
            
        # Skip devices without an ID
        device_id = device.get("id")
        if not device_id:
            _LOGGER.warning("Network device missing ID")
            continue
            
        _LOGGER.debug("Processing network device: %s", device_id)
            
        device_gid = device.get("gid")
        if not device_gid or device_gid not in firewalla_devices:
            _LOGGER.warning("Network device has invalid GID: %s", device_gid)
            continue
            
        firewalla_device = firewalla_devices[device_gid]
        firewalla_name = firewalla_device.get("name", "Firewalla")
        
        try:
            # Network device online status
            entities.append(
                NetworkDeviceOnlineSensor(
                    coordinator=coordinator,
                    device_data=device,
                    firewalla_name=firewalla_name,
                )
            )
            
            # Download data sensor
            entities.append(
                NetworkDeviceDownloadSensor(
                    coordinator=coordinator,
                    device_data=device,
                    firewalla_name=firewalla_name,
                )
            )
            
            # Upload data sensor
            entities.append(
                NetworkDeviceUploadSensor(
                    coordinator=coordinator,
                    device_data=device,
                    firewalla_name=firewalla_name,
                )
            )
            
        except Exception as ex:
            _LOGGER.error("Error creating network device sensor: %s - %s", device_id, ex)
    
    _LOGGER.debug("Adding %d network device entities", len(entities))
    if entities:
        async_add_entities(entities)
    else:
        _LOGGER.warning("No network device entities were created")



class NetworkDeviceBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for network device sensors."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, coordinator, device_data, firewalla_name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.device_data = device_data
        self.device_id = device_data["id"]
        self.gid = device_data["gid"]
        self.firewalla_name = firewalla_name
        
        # Generate a safe ID by replacing invalid characters
        safe_id = self.device_id.replace(":", "_").replace(".", "_")
        
        # Set up common attributes
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            name=device_data.get("name", self.device_id),
            manufacturer=device_data.get("macVendor", "Unknown"),
            via_device=(DOMAIN, self.gid),
            model="Network Device",
        )
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        # Find current device data
        current_device = None
        if self.coordinator.data and "network_devices" in self.coordinator.data:
            for device in self.coordinator.data["network_devices"]:
                if device.get("id") == self.device_id:
                    current_device = device
                    break
        
        if not current_device:
            current_device = self.device_data
        
        attributes = {
            "ip": current_device.get("ip", ""),
            "mac": self.device_id.replace("mac:", ""),
            "firewalla_device": self.firewalla_name,
        }
        
        # Add network information
        network = current_device.get("network", {})
        if isinstance(network, dict) and "name" in network:
            attributes["network"] = network["name"]
        
        # Add group information
        group = current_device.get("group", {})
        if isinstance(group, dict) and "name" in group:
            attributes["group"] = group["name"]
        
        # Add last seen timestamp in ISO format
        if "lastSeen" in current_device:
            try:
                last_seen = float(current_device["lastSeen"])
                last_seen_iso = datetime.fromtimestamp(last_seen).isoformat()
                attributes["last_seen"] = last_seen_iso
            except (ValueError, TypeError):
                attributes["last_seen"] = current_device["lastSeen"]
        
        # Add IP reservation status
        if "ipReserved" in current_device:
            attributes["ip_reserved"] = current_device["ipReserved"]
            
        return attributes
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False
            
        if self.coordinator.data and "network_devices" in self.coordinator.data:
            for device in self.coordinator.data["network_devices"]:
                if device.get("id") == self.device_id:
                    return True
        
        return False


class NetworkDeviceOnlineSensor(NetworkDeviceBaseSensor):
    """Sensor for network device online status."""
    
    _attr_icon = "mdi:lan-connect"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["online", "offline"]
    
    def __init__(self, coordinator, device_data, firewalla_name):
        """Initialize the sensor."""
        super().__init__(coordinator, device_data, firewalla_name)
        self._attr_unique_id = f"{self.device_id}_online"
        self._attr_name = f"{device_data.get('name', self.device_id)} Status"
    
    @property
    def native_value(self) -> str:
        """Return the online status."""
        if self.coordinator.data and "network_devices" in self.coordinator.data:
            for device in self.coordinator.data["network_devices"]:
                if device.get("id") == self.device_id:
                    return "online" if device.get("online", False) else "offline"
        
        return "offline"


class NetworkDeviceDownloadSensor(NetworkDeviceBaseSensor):
    """Sensor for network device download data."""
    
    _attr_icon = "mdi:download"
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfInformation.BYTES
    
    def __init__(self, coordinator, device_data, firewalla_name):
        """Initialize the sensor."""
        super().__init__(coordinator, device_data, firewalla_name)
        self._attr_unique_id = f"{self.device_id}_download"
        self._attr_name = f"{device_data.get('name', self.device_id)} Download"
    
    @property
    def native_value(self) -> int:
        """Return the download data."""
        if self.coordinator.data and "network_devices" in self.coordinator.data:
            for device in self.coordinator.data["network_devices"]:
                if device.get("id") == self.device_id:
                    return device.get("totalDownload", 0)
        
        return 0


class NetworkDeviceUploadSensor(NetworkDeviceBaseSensor):
    """Sensor for network device upload data."""
    
    _attr_icon = "mdi:upload"
    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfInformation.BYTES
    
    def __init__(self, coordinator, device_data, firewalla_name):
        """Initialize the sensor."""
        super().__init__(coordinator, device_data, firewalla_name)
        self._attr_unique_id = f"{self.device_id}_upload"
        self._attr_name = f"{device_data.get('name', self.device_id)} Upload"
    
    @property
    def native_value(self) -> int:
        """Return the upload data."""
        if self.coordinator.data and "network_devices" in self.coordinator.data:
            for device in self.coordinator.data["network_devices"]:
                if device.get("id") == self.device_id:
                    return device.get("totalUpload", 0)
        
        return 0
