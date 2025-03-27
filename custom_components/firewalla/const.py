"""Constants for the Firewalla integration."""
from typing import Final

# Integration Constants
DOMAIN: Final = "firewalla"
FIREWALLA_COORDINATOR: Final = "coordinator"

# Device Attributes
ATTR_GID: Final = "gid"
ATTR_MODEL: Final = "model"
ATTR_VERSION: Final = "version"
ATTR_MODE: Final = "mode"
ATTR_PUBLIC_IP: Final = "public_ip"
ATTR_LAST_SEEN: Final = "last_seen"
ATTR_LOCATION: Final = "location"
ATTR_LICENSE: Final = "license"

# Rule Attributes
ATTR_RULE_ID: Final = "id"
ATTR_RULE_TYPE: Final = "type"
ATTR_RULE_TARGET: Final = "target"
ATTR_RULE_ACTION: Final = "action"
ATTR_RULE_DISABLED: Final = "disabled"
ATTR_RULE_PAUSED: Final = "paused"
ATTR_RULE_CREATED_TIME: Final = "created_time"
ATTR_RULE_UPDATED_TIME: Final = "updated_time"
ATTR_RULE_NOTES: Final = "notes"

# Network Device Attributes
ATTR_DEVICE_MAC: Final = "mac"
ATTR_DEVICE_NAME: Final = "name"
ATTR_DEVICE_VENDOR: Final = "vendor"
ATTR_DEVICE_ACTIVE: Final = "active"
ATTR_DEVICE_IP: Final = "ip"
ATTR_DEVICE_LAST_ACTIVE: Final = "last_active"

# Entity Types
ENTITY_DEVICE_COUNT: Final = "device_count"
ENTITY_RULE_COUNT: Final = "rule_count"
ENTITY_ALARM_COUNT: Final = "alarm_count"
ENTITY_ONLINE: Final = "online"
ENTITY_RULE: Final = "rule"
ENTITY_NETWORK_DEVICE: Final = "network_device"

# Services
SERVICE_PAUSE_RULE: Final = "pause_rule"
SERVICE_RESUME_RULE: Final = "resume_rule"

# Default Values
DEFAULT_SCAN_INTERVAL: Final = 60  # seconds
