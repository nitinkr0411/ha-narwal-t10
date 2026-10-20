"""Home Assistant-level constants for the Narwal T10 integration."""

from __future__ import annotations

DOMAIN = "narwal_t10"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"  # noqa: S105 - config key name, not a secret value
CONF_REGION = "region"
CONF_DEVICE_ID = "device_id"  # robot_id
CONF_MACHINE_ID = "machine_id"
CONF_DEVICE_NAME = "device_name"

PLATFORMS = ["vacuum", "sensor", "binary_sensor", "image"]

MANUFACTURER = "Narwal"
MODEL = "T10"
