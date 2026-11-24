"""Constants for the Efilos VMC integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "efilos_vmc"
MANUFACTURER: Final = "Efilos"
MODEL: Final = "Controlador TS IP"

CONF_UNIT_ID: Final = "unit_id"
CONF_SPEED_CONTROL: Final = "speed_control"
CONF_FAN_FEEDBACK: Final = "fan_feedback"
CONF_AUTO_PRESET: Final = "auto_preset"

SPEED_CONTROL_VARIABLE: Final = "variable"
SPEED_CONTROL_THREE_SPEED: Final = "three_speed"
SPEED_CONTROLS: Final = (SPEED_CONTROL_VARIABLE, SPEED_CONTROL_THREE_SPEED)

FAN_FEEDBACK_RPM: Final = "rpm"
FAN_FEEDBACK_PERCENT: Final = "percent"
FAN_FEEDBACKS: Final = (FAN_FEEDBACK_RPM, FAN_FEEDBACK_PERCENT)

DEFAULT_PORT: Final = 502
DEFAULT_UNIT_ID: Final = 1

# The controller drops Modbus-written values when no register has been read
# for its disconnection timeout (10 s by default, register 8503). Polling every
# 5 s keeps the session alive.
UPDATE_INTERVAL: Final = timedelta(seconds=5)

PRESET_SCHEDULE: Final = "schedule"
PRESET_AUTO: Final = "auto"
