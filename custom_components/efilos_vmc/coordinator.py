"""Polling coordinator for the Efilos VMC."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL
from .modbus import ModbusError, ModbusExceptionResponse, ModbusTcpClient
from .registers import (
    POLL_BLOCKS,
    REG_SW_VERSION_0,
    VmcData,
    format_software_version,
)

_LOGGER = logging.getLogger(__name__)

type EfilosConfigEntry = ConfigEntry[EfilosCoordinator]


class EfilosCoordinator(DataUpdateCoordinator[VmcData]):
    """Reads the controller's registers every few seconds and handles writes."""

    config_entry: EfilosConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: EfilosConfigEntry, client: ModbusTcpClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client
        self.software_version: str | None = None
        # Blocks the device rejected as a whole; read register by register.
        self._split_blocks: set[int] = set()

    async def _async_setup(self) -> None:
        try:
            ver0, ver1 = await self.client.read_holding_registers(REG_SW_VERSION_0 - 1, 2)
        except ModbusError as err:
            _LOGGER.debug("Could not read software version: %s", err)
        else:
            self.software_version = format_software_version(ver0, ver1)

    async def _async_update_data(self) -> VmcData:
        blocks: dict[int, list[int]] = {}
        try:
            for start, count in POLL_BLOCKS:
                if start in self._split_blocks:
                    blocks.update(await self._read_one_by_one(start, count))
                    continue
                try:
                    blocks[start] = await self.client.read_holding_registers(start - 1, count)
                except ModbusExceptionResponse as err:
                    _LOGGER.debug(
                        "Block read at register %s rejected (%s), reading registers one by one",
                        start,
                        err,
                    )
                    self._split_blocks.add(start)
                    blocks.update(await self._read_one_by_one(start, count))
        except ModbusError as err:
            raise UpdateFailed(f"Error communicating with the VMC: {err}") from err
        return VmcData.from_blocks(blocks)

    async def _read_one_by_one(self, start: int, count: int) -> dict[int, list[int]]:
        result: dict[int, list[int]] = {}
        for register in range(start, start + count):
            try:
                result[register] = await self.client.read_holding_registers(register - 1, 1)
            except ModbusExceptionResponse:
                continue
        return result

    async def async_write_register(self, register: int, value: int) -> None:
        """Write one register (manual numbering) and refresh."""
        try:
            await self.client.write_register(register - 1, value)
        except ModbusError as err:
            raise HomeAssistantError(f"Could not write to the VMC: {err}") from err
        await self.async_request_refresh()

    async def async_update_bits(self, register: int, mask: int, bits: int) -> None:
        """Change only the bits in ``mask`` of one register and refresh."""
        try:
            await self.client.update_bits(register - 1, mask, bits)
        except ModbusError as err:
            raise HomeAssistantError(f"Could not write to the VMC: {err}") from err
        await self.async_request_refresh()
