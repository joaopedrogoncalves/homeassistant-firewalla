"""Binary sensor platform for Firewalla integration."""
from __future__ import annotations

from typing import Any, Dict

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
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
    ATTR_MODE,
    ATTR_MODEL,
    ATTR_PUBLIC_IP,
    ATTR_VERSION,
    DOMAIN,
    ENTITY_ONLINE,
    FIREWALLA_COORDINATOR,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Firewalla binary sensor entries."""
    coordinator = hass.data[DOMAIN][entry.entry_id][FIREWALLA_COORDINATOR]
    
    entities = []
    
    for device_data in coordinator.data:
        # Add online status binary sensor
        entities.append(
            FirewallaOnlineSensor(
                coordinator=coordinator,
                device_data=device_data,
            )
        )

    async_add_entities(entities)


class FirewallaOnlineSensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Firewalla online status sensor."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    
    def __init__(self, coordinator, device_data):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.device_data = device_data
        self.gid = device_data["gid"]
        self._attr_unique_id = f"{self.gid}_{ENTITY_ONLINE}"
        self._attr_name = f"{device_data['name']} Online"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.gid)},
            name=device_data["name"],
            manufacturer="Firewalla",
            model=device_data["model"].capitalize(),
            sw_version=device_data["version"],
            configuration_url=f"https://my.firewalla.com/app/box/{self.gid}",
        )

    @property
    def is_on(self) -> bool:
        """Return true if the Firewalla is online."""
        for device in self.coordinator.data:
            if device["gid"] == self.gid:
                return device["online"]
        return False
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the extra state attributes of the entity."""
        for device in self.coordinator.data:
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
            
        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False
            
        for device in self.coordinator.data:
            if device["gid"] == self.gid:
                return True
        return False
