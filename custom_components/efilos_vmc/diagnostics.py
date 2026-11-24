"""Diagnostics for the Efilos VMC: config, decoded state and a raw register dump."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .coordinator import EfilosConfigEntry
from .modbus import ModbusError, ModbusExceptionResponse

TO_REDACT = {CONF_HOST}

# Every register range in the manual's table, plus register 7, which the
# manual mentions but doesn't list. Dumped one by one so a model that
# rejects some registers still reports the rest.
DUMP_RANGES: tuple[tuple[int, int], ...] = (
    (1, 7),
    (14, 14),
    (20, 20),
    (24, 27),
    (51, 56),
    (81, 100),
)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: EfilosConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    data = coordinator.data

    registers: dict[str, int | str] = {}
    for first, last in DUMP_RANGES:
        for register in range(first, last + 1):
            try:
                (value,) = await coordinator.client.read_holding_registers(register - 1, 1)
            except ModbusExceptionResponse as err:
                registers[str(register)] = f"exception {err.code}"
            except ModbusError as err:
                registers[str(register)] = f"error: {err}"
            else:
                registers[str(register)] = value

    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "software_version": coordinator.software_version,
        "last_update_success": coordinator.last_update_success,
        "decoded": {
            "fans_on": data.fans_on,
            "speed_set_point": data.speed_set_point,
            "season": data.season,
            "bypass_mode": data.bypass_mode,
            "temperatures": {
                str(register): data.temperature(register) for register in (81, 82, 83, 84, 85)
            },
            "fan_hours": data.fan_hours,
            "active_alarms": data.active_alarms,
        },
        "registers": registers,
    }
