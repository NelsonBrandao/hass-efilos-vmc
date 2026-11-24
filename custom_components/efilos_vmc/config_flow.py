"""Config flow for the Efilos VMC."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import (
    CONF_FAN_FEEDBACK,
    CONF_SPEED_CONTROL,
    CONF_UNIT_ID,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
    DOMAIN,
    FAN_FEEDBACK_PERCENT,
    FAN_FEEDBACK_RPM,
    FAN_FEEDBACKS,
    SPEED_CONTROL_VARIABLE,
    SPEED_CONTROLS,
)
from .modbus import ModbusError, ModbusTcpClient
from .registers import REG_SPEED_SUPPLY, REG_TEMP_OUTDOOR

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Efilos VMC"


def _connection_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, vol.UNDEFINED)): TextSelector(),
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): NumberSelector(
                NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)
            ),
            vol.Required(
                CONF_UNIT_ID, default=defaults.get(CONF_UNIT_ID, DEFAULT_UNIT_ID)
            ): NumberSelector(NumberSelectorConfig(min=0, max=255, mode=NumberSelectorMode.BOX)),
        }
    )


def _options_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_SPEED_CONTROL, default=defaults.get(CONF_SPEED_CONTROL, SPEED_CONTROL_VARIABLE)
            ): SelectSelector(
                SelectSelectorConfig(
                    options=list(SPEED_CONTROLS),
                    translation_key=CONF_SPEED_CONTROL,
                    mode=SelectSelectorMode.LIST,
                )
            ),
            vol.Required(
                CONF_FAN_FEEDBACK, default=defaults.get(CONF_FAN_FEEDBACK, FAN_FEEDBACK_RPM)
            ): SelectSelector(
                SelectSelectorConfig(
                    options=list(FAN_FEEDBACKS),
                    translation_key=CONF_FAN_FEEDBACK,
                    mode=SelectSelectorMode.LIST,
                )
            ),
        }
    )


def _normalise(user_input: dict[str, Any]) -> dict[str, Any]:
    return {
        CONF_HOST: str(user_input[CONF_HOST]).strip(),
        CONF_PORT: int(user_input[CONF_PORT]),
        CONF_UNIT_ID: int(user_input[CONF_UNIT_ID]),
    }


async def _probe(data: dict[str, Any]) -> str:
    """Check the controller answers and work out the fan feedback unit.

    Returns the detected fan feedback unit. Raises ModbusError when the
    controller cannot be reached.
    """
    client = ModbusTcpClient(data[CONF_HOST], data[CONF_PORT], data[CONF_UNIT_ID])
    try:
        await client.read_holding_registers(REG_TEMP_OUTDOOR - 1, 1)
        # Register 7 B08 is documented as the rpm flag, but a real unit reports rpm with it cleared.
        (speed,) = await client.read_holding_registers(REG_SPEED_SUPPLY - 1, 1)
        if 0 < speed <= 100:
            return FAN_FEEDBACK_PERCENT
        return FAN_FEEDBACK_RPM
    finally:
        await client.close()


class EfilosConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up an Efilos VMC from the UI."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._detected_feedback = FAN_FEEDBACK_RPM

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> EfilosOptionsFlow:
        return EfilosOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data = _normalise(user_input)
            await self.async_set_unique_id(f"{data[CONF_HOST]}:{data[CONF_PORT]}:{data[CONF_UNIT_ID]}")
            self._abort_if_unique_id_configured()
            try:
                self._detected_feedback = await _probe(data)
            except ModbusError as err:
                _LOGGER.debug("Connection test failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                self._data = data
                return await self.async_step_fans()

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                _connection_schema({}), user_input or {}
            ),
            errors=errors,
        )

    async def async_step_fans(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title=DEFAULT_NAME, data=self._data, options=user_input)
        return self.async_show_form(
            step_id="fans",
            data_schema=_options_schema({CONF_FAN_FEEDBACK: self._detected_feedback}),
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = _normalise(user_input)
            await self.async_set_unique_id(f"{data[CONF_HOST]}:{data[CONF_PORT]}:{data[CONF_UNIT_ID]}")
            if entry.unique_id != self.unique_id:
                self._abort_if_unique_id_configured()
            try:
                await _probe(data)
            except ModbusError as err:
                _LOGGER.debug("Connection test failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry, unique_id=self.unique_id, data_updates=data
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_connection_schema(dict(entry.data)),
            errors=errors,
        )


class EfilosOptionsFlow(OptionsFlowWithReload):
    """Change how fan speed is controlled and reported."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(dict(self.config_entry.options)),
        )
