"""Switch platform for Firewalla integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .entity_base import FirewallaBaseEntity, FirewallaRuleEntity

from .const import (
    ATTR_GID,
    ATTR_RULE_ACTION,
    ATTR_RULE_CREATED_TIME,
    ATTR_RULE_DISABLED,
    ATTR_RULE_ID,
    ATTR_RULE_NOTES,
    ATTR_RULE_TARGET,
    ATTR_RULE_TYPE,
    DOMAIN,
    ENTITY_RULE,
    FIREWALLA_COORDINATOR,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Firewalla switch entries."""
    coordinator = hass.data[DOMAIN][entry.entry_id][FIREWALLA_COORDINATOR]
    
    # Ensure we have rules data
    if not coordinator.data:
        _LOGGER.error("No coordinator data available")
        return
        
    if "rules" not in coordinator.data:
        _LOGGER.error("No rules data in coordinator: %s", coordinator.data.keys() if coordinator.data else "No data")
        return
    
    # Log the data structure for debugging
    _LOGGER.debug("Rules data available: %d rules", 
                 len(coordinator.data["rules"]) if isinstance(coordinator.data["rules"], list) else 0)
    
    # Create a mapping of device GIDs to device info
    device_mapping = {}
    if "devices" in coordinator.data and isinstance(coordinator.data["devices"], list):
        for device in coordinator.data["devices"]:
            if isinstance(device, dict) and "gid" in device:
                device_mapping[device["gid"]] = device
    
    entities = []
    
    # Create switch entities for each rule
    for rule in coordinator.data["rules"]:
        # Ensure rule is a dictionary
        if not isinstance(rule, dict):
            _LOGGER.error("Unexpected rule data format: %s", type(rule))
            continue
            
        # Skip disabled rules
        if not isinstance(rule, dict) or rule.get("disabled", False):
            continue
            
        # Get the device info for this rule
        device_gid = rule.get("gid")
        if not device_gid or device_gid not in device_mapping:
            _LOGGER.warning("Rule has no device GID or device not found: %s", rule.get("id", "unknown"))
            continue
            
        device_info = device_mapping[device_gid]
        
        try:
            entities.append(
                FirewallaRuleSwitch(
                    coordinator=coordinator,
                    rule=rule,
                    device_info=device_info,
                )
            )
        except Exception as ex:
            _LOGGER.error("Error creating FirewallaRuleSwitch: %s", ex)

    _LOGGER.info("Adding %d rule switch entities", len(entities))
    async_add_entities(entities)


class FirewallaRuleSwitch(FirewallaRuleEntity, SwitchEntity):
    """Representation of a Firewalla rule switch."""
    
    _attr_icon = "mdi:shield"
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_has_entity_name = True

    def __init__(self, coordinator, rule, device_info):
        """Initialize the switch."""
        super().__init__(coordinator, rule, device_info)
        
        # Determine icon based on action (allow/block)
        action = rule.get("action", "").lower()
        if action == "allow":
            self._attr_icon = "mdi:checkbox-multiple-marked-circle"
        elif action == "block" or action == "deny":
            self._attr_icon = "mdi:block-helper"
        elif action == "timelimit":
            self._attr_icon = "mdi:clock"
        else:
            self._attr_icon = "mdi:shield"
        
        # Create a descriptive name based on the rule notes, group, or type and target
        rule_type = rule.get("type", "unknown")
        rule_target = rule.get("target", "unknown")
        
        # Get target value if it's a dictionary
        if isinstance(rule_target, dict):
            target_value = rule_target.get("value", "unknown")
            target_type = rule_target.get("type", "")
            if target_type and target_value:
                target_str = f"{target_type}: {target_value}"
            else:
                target_str = target_value
        else:
            target_str = str(rule_target)
            
        # Get notes and group information
        rule_notes = rule.get("notes", "")
        device_name = device_info.get("name", "Firewalla")
        
        # Check for group name in scope
        group_name = ""
        scope = rule.get("scope", {})
        if isinstance(scope, dict) and scope.get("type") == "group":
            group_id = scope.get("value")
            if group_id and coordinator.data and "device_groups" in coordinator.data:
                group_name = coordinator.data["device_groups"].get(group_id, "")
        
        # Create name with the most descriptive information available
        name_parts = []
        
        # Add notes if available, otherwise use target info
        if rule_notes:
            name_parts.append(rule_notes)
        else:
            if target_type == "category":
                name_parts.append(f"category: {target_value}")
            elif target_str and target_str != "unknown":
                name_parts.append(target_str)
        
        # Add group name if available
        if group_name:
            name_parts.insert(0, f"group: {group_name}")
            
        # Construct final name
        name = " - ".join(name_parts)
        self._attr_name = f"Rule: {name}"
        
        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.device_gid)},
            name=device_info.get("name", "Firewalla"),
            manufacturer="Firewalla",
            model=device_info.get("model", "").capitalize(),
            sw_version=device_info.get("version", ""),
            configuration_url=f"https://my.firewalla.com/app/box/{self.device_gid}",
        )

    @property
    def is_on(self) -> bool:
        """Return true if the rule is active (not paused)."""
        # First, check if there's an updated version of the rule in current data
        current_rule = self.get_rule_data()
        
        if current_rule:
            # Check the status field first (seems to be what the API uses)
            if "status" in current_rule:
                rule_status = current_rule["status"]
                _LOGGER.debug("Rule %s has status: %s", self.rule_id, rule_status)
                return rule_status != "paused"
            
            # Fallback to paused field
            return not current_rule.get("paused", False)
        else:
            # Fall back to the original rule data if not found in current data
            if "status" in self.rule:
                rule_status = self.rule["status"]
                _LOGGER.debug("Using original rule status for %s: %s", self.rule_id, rule_status)
                return rule_status != "paused"
            return not self.rule.get("paused", False)
            


    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes about the rule."""
        # Find the current rule data
        current_rule = self.get_rule_data()
                
        if not current_rule:
            current_rule = self.rule
            
        attributes = {
            ATTR_RULE_ID: current_rule.get("id", "unknown"),
            ATTR_GID: current_rule.get("gid", "unknown"),
            "status": "active" if self.is_on else "paused",
        }
        
        # Add MSP link to the rule
        msp_domain = self.coordinator.api.host
        rule_id = current_rule.get("id", "")
        if msp_domain and rule_id:
            attributes["msp_url"] = f"https://{msp_domain}/global/rules?filters={rule_id}"
        
        # Add action
        if "action" in current_rule:
            attributes[ATTR_RULE_ACTION] = current_rule["action"]
        
        # Add target information
        target = current_rule.get("target", {})
        if isinstance(target, dict):
            target_type = target.get("type")
            target_value = target.get("value")
            if target_type:
                attributes["target_type"] = target_type
            if target_value:
                attributes["target_value"] = target_value
            
            # Add any other interesting target fields
            for key, value in target.items():
                if key not in ["type", "value"]:
                    attributes[f"target_{key}"] = value
        
        # Add scope information
        scope = current_rule.get("scope", {})
        if isinstance(scope, dict):
            scope_type = scope.get("type")
            scope_value = scope.get("value")
            if scope_type:
                attributes["scope_type"] = scope_type
            if scope_value:
                attributes["scope_value"] = scope_value
                
            # If the scope is a group, add the group name
            if scope_type == "group" and scope_value and self.coordinator.data and "device_groups" in self.coordinator.data:
                group_name = self.coordinator.data["device_groups"].get(scope_value)
                if group_name:
                    attributes["group_name"] = group_name
        
        # Add direction if available
        if "direction" in current_rule:
            attributes["direction"] = current_rule["direction"]
            
        # Add disabled flag
        if "disabled" in current_rule:
            attributes[ATTR_RULE_DISABLED] = current_rule["disabled"]
            
        # Add notes if available
        if "notes" in current_rule and current_rule["notes"]:
            attributes[ATTR_RULE_NOTES] = current_rule["notes"]
            
        # Add timestamps in ISO 8601 format
        from datetime import datetime
        
        if "ts" in current_rule and current_rule["ts"]:
            try:
                created_at = datetime.fromtimestamp(current_rule["ts"]).isoformat()
                attributes["created_at"] = created_at
            except (ValueError, TypeError):
                # Keep original value if conversion fails
                attributes["created_at"] = current_rule["ts"]
                
        if "updateTs" in current_rule and current_rule["updateTs"]:
            try:
                updated_at = datetime.fromtimestamp(current_rule["updateTs"]).isoformat()
                attributes["updated_at"] = updated_at
            except (ValueError, TypeError):
                # Keep original value if conversion fails
                attributes["updated_at"] = current_rule["updateTs"]
                
        if "createdAt" in current_rule:
            # This might already be in a different format, so keep as is
            attributes[ATTR_RULE_CREATED_TIME] = current_rule["createdAt"]
            
        return attributes

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch (resume the rule)."""
        _LOGGER.debug("Resuming rule: %s", self.rule_id)
        success = await self.coordinator.api.resume_rule(self.rule_id)
        
        if success:
            # Update local state immediately for faster UI feedback
            current_rule = self.get_rule_data()
            if current_rule:
                current_rule["status"] = "active"  # Set status directly
                current_rule["paused"] = False     # Also set paused for backward compatibility
            
            # Also update our cached rule
            self.rule["status"] = "active"
            self.rule["paused"] = False
            
            # Force state update
            self.async_write_ha_state()
            
            # Then refresh data from API
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to resume rule: %s", self.rule_id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch (pause the rule)."""
        _LOGGER.debug("Pausing rule: %s", self.rule_id)
        success = await self.coordinator.api.pause_rule(self.rule_id)
        
        if success:
            # Update local state immediately for faster UI feedback
            current_rule = self.get_rule_data()
            if current_rule:
                current_rule["status"] = "paused"  # Set status directly
                current_rule["paused"] = True      # Also set paused for backward compatibility
            
            # Also update our cached rule
            self.rule["status"] = "paused"
            self.rule["paused"] = True
            
            # Force state update
            self.async_write_ha_state()
            
            # Then refresh data from API
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to pause rule: %s", self.rule_id)

