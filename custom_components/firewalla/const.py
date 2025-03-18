"""Constants for the Firewalla integration."""

DOMAIN = "firewalla"
FIREWALLA_COORDINATOR = "coordinator"

# Sensor attributes
ATTR_MODEL = "model"
ATTR_VERSION = "version"
ATTR_MODE = "mode"
ATTR_PUBLIC_IP = "public_ip"
ATTR_LAST_SEEN = "last_seen"
ATTR_LOCATION = "location"
ATTR_LICENSE = "license"
ATTR_GID = "gid"

# Rule attributes
ATTR_RULE_ID = "id"
ATTR_RULE_TYPE = "type"
ATTR_RULE_TARGET = "target"
ATTR_RULE_ACTION = "action"
ATTR_RULE_DISABLED = "disabled"
ATTR_RULE_PAUSED = "paused"
ATTR_RULE_CREATED_TIME = "created_time"
ATTR_RULE_UPDATED_TIME = "updated_time"
ATTR_RULE_NOTES = "notes"

# Entity types
ENTITY_DEVICE_COUNT = "device_count"
ENTITY_RULE_COUNT = "rule_count"
ENTITY_ALARM_COUNT = "alarm_count"
ENTITY_ONLINE = "online"
ENTITY_RULE = "rule"
ENTITY_NETWORK_DEVICE = "network_device"

# Services
SERVICE_PAUSE_RULE = "pause_rule"
SERVICE_RESUME_RULE = "resume_rule"
