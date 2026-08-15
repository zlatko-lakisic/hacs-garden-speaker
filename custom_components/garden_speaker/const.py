"""Constants for the Garden Speaker integration."""

from datetime import timedelta

DOMAIN = "garden_speaker"

CONF_API_KEY = "api_key"
CONF_PORT = "port"

DEFAULT_HOST = "192.168.89.27"
DEFAULT_PORT = 8090
DEFAULT_SCAN_INTERVAL = timedelta(seconds=45)

SERVICE_HEALTH_CHECK = "health_check"
SERVICE_REPAIR = "repair"
SERVICE_REPAIR_PAIRING = "repair_pairing"
SERVICE_RESTART_STACK = "restart_stack"

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_CONFIRM_PAIRING_MODE = "confirm_pairing_mode"
ATTR_INCLUDE_CONTROL_API = "include_control_api"

PAIRING_INSTRUCTIONS = (
    "Hold the JBL PartyBox Bluetooth button for 3–5 seconds until the LED "
    "blinks rapidly, and turn off Bluetooth on nearby phones so they do not "
    "take the connection."
)
