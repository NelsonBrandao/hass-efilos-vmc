"""Tests for the Modbus TCP client and register decoding."""

from __future__ import annotations

import pytest

from custom_components.efilos_vmc.modbus import (
    ModbusConnectionError,
    ModbusExceptionResponse,
    ModbusTcpClient,
)
from custom_components.efilos_vmc.registers import VmcData, decode_temperature, set_bits

from .fake_vmc import FakeVmc


async def test_read_and_write(fake_vmc: FakeVmc) -> None:
    client = ModbusTcpClient("127.0.0.1", fake_vmc.port)
    assert await client.read_holding_registers(80, 4) == [166, 194, 181, 196]
    await client.write_register(50, 60)
    assert fake_vmc.registers[51] == 60
    assert await client.read_holding_registers(50, 1) == [60]
    await client.close()


async def test_exception_response(fake_vmc: FakeVmc) -> None:
    client = ModbusTcpClient("127.0.0.1", fake_vmc.port)
    with pytest.raises(ModbusExceptionResponse) as err:
        await client.read_holding_registers(9, 1)  # register 10 isn't defined
    assert err.value.code == 2
    # The connection is still usable after an exception response.
    assert await client.read_holding_registers(19, 1) == [1]
    await client.close()


async def test_update_bits_keeps_other_bits(fake_vmc: FakeVmc) -> None:
    fake_vmc.registers[20] = 0b0100_0001  # winter + post-treatment off
    client = ModbusTcpClient("127.0.0.1", fake_vmc.port)
    assert await client.update_bits(19, 0b1100, 0b1000) == 0b0100_1001
    assert fake_vmc.registers[20] == 0b0100_1001
    # No write when nothing changes.
    writes = len(fake_vmc.writes)
    await client.update_bits(19, 0b1100, 0b1000)
    assert len(fake_vmc.writes) == writes
    await client.close()


async def test_reconnects_after_device_drops_connection(fake_vmc: FakeVmc) -> None:
    client = ModbusTcpClient("127.0.0.1", fake_vmc.port)
    assert await client.read_holding_registers(50, 1) == [35]
    await fake_vmc.drop_clients()
    assert await client.read_holding_registers(50, 1) == [35]
    await client.close()


async def test_connection_refused() -> None:
    client = ModbusTcpClient("127.0.0.1", 1, timeout=1)
    with pytest.raises(ModbusConnectionError):
        await client.read_holding_registers(0, 1)


def test_decode_temperature() -> None:
    assert decode_temperature(166) == 16.6
    assert decode_temperature(0xFFEC) == -2.0
    assert decode_temperature(0x7FFF) is None  # missing probe
    assert decode_temperature(None) is None


def test_set_bits() -> None:
    assert set_bits(0xFFFF, 0b1100, 0) == 0xFFF3
    assert set_bits(0b100111, 12, 8) == 0b101011


def test_vmc_data_decoding() -> None:
    data = VmcData.from_blocks({20: [0b1001], 90: [0b0011_0000], 95: [1, 2]})
    assert data.season == "winter"
    assert data.bypass_mode == "open"
    assert data.fans_on is True
    assert data.fan_hours == 65538
    assert data.active_alarms == ["filters", "fans"]
    assert data.general_alarm is True

    only_filters = VmcData.from_blocks({90: [0b0001_0000], 97: [1 << 9]})
    assert only_filters.active_alarms == ["filters"]
    assert only_filters.general_alarm is False
