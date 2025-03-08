"""Switch platform for Firewalla integration."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import (
    ATTR_GID,
    ATTR_RULE_ACTION,
    ATTR_RULE_CREATED_TIME,
    ATTR_RULE_DISABLED,
    ATTR_RULE_ID,
    ATTR_RULE_TARGET,
    ATTR_RULE_TYPE,
    DOMAIN,
    ENTITY_RULE,
    FIREWALLA_COORDINATOR,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Firewalla switch entries."""
    coordinator = hass.data[DOMAIN][entry.entry_id][FIREWALLA_COORDINATOR]
    
    if not coordinator.data or "rules" not in coordinator.data:
        return
    
    # Create a mapping of device GIDs to device info
    device_mapping = {}
    for device in coordinator.data["devices"]:
        device_mapping[device["gid"]] = device
    
    entities = []
    
    # Create switch entities for each rule
    for rule in coordinator.data["rules"]:
        # Skip disabled rules
        if rule.get("disabled", False):
            continue
            
        # Get the device info for this rule
        device_gid = rule.get("gid")
        if device_gid not in device_mapping:
            continue
            
        device_info = device_mapping[device_gid]
        
        entities.append(
            FirewallaRuleSwitch(
                coordinator=coordinator,
                rule=rule,
                device_info=device_info,
            )
        )

    async_add_entities(entities)


class FirewallaRuleSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Firewalla rule switch."""
    
    _attr_icon = "mdi:shield"

    def __init__(self, coordinator, rule, device_info):
        """Initialize the switch."""
        super().__init__(coordinator)
        self.rule = rule
        self.rule_id = rule["id"]
        self.device_gid = rule["gid"]
        self.device_info = device_info
        
        # Create a unique ID based on the rule ID
        self._attr_unique_id = f"{self.device_gid}_{ENTITY_RULE}_{self.rule_id}"
        
        # Create a descriptive name based on the rule type and target
        rule_type = rule.get("type", "unknown")
        rule_target = rule.get("target", "unknown")
        self._attr_name = f"{device_info['name']} Rule: {rule_type} - {rule_target}"
        
        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.device_gid)},
            name=device_info["name"],
            manufacturer="Firewalla",
            model=device_info["model"].capitalize(),
            sw_version=device_info["version"],
            configuration_url=f"https://my.firewalla.com/app/box/{self.device_gid}",
        )

    @property
    def is_on(self) -> bool:
        """Return true if the rule is active (not paused)."""
        # Find the current rule state in coordinator data
        for rule in self.coordinator.data["rules"]:
            if rule["id"] == self.rule_id:
                # Rule is considered "on" when not paused
                return not rule.get("paused", False)
        return False

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes about the rule."""
        # Find the current rule data
        current_rule = None
        for rule in self.coordinator.data["rules"]:
            if rule["id"] == self.rule_id:
                current_rule = rule
                break
                
        if not current_rule:
            return {}
            
        attributes = {
            ATTR_RULE_ID: current_rule["id"],
            ATTR_GID: current_rule["gid"],
            ATTR_RULE_TYPE: current_rule.get("type", "unknown"),
            ATTR_RULE_TARGET: current_rule.get("target", "unknown"),
            ATTR_RULE_ACTION: current_rule.get("action", "unknown"),
            ATTR_RULE_DISABLED: current_rule.get("disabled", False),
        }
        
        if "createdAt" in current_rule:
            attributes[ATTR_RULE_CREATED_TIME] = current_rule["createdAt"]
            
        return attributes

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch (resume the rule)."""
        await self.coordinator.api.resume_rule(self.rule_id)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch (pause the rule)."""
        await self.coordinator.api.pause_rule(self.rule_id)
        await self.coordinator.async_request_refresh()

    @property
    def available(self) -> bool:
        """Return if the entity is available."""
        if not self.coordinator.last_update_success:
            return False
            
        # Check if the device is still available
        device_available = False
        for device in self.coordinator.data["devices"]:
            if device["gid"] == self.device_gid and device["online"]:
                device_available = True
                break
                
        if not device_available:
            return False
            
        # Check if the rule still exists
        for rule in self.coordinator.data["rules"]:
            if rule["id"] == self.rule_id:
                return True
                
        return False
