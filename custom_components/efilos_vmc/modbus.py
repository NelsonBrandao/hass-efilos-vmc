"""Minimal async Modbus TCP client for the Efilos TS IP controller.

Only the two function codes the integration needs are implemented:
03 (read holding registers) and 06 (write single register). Keeping our own
client avoids pinning a pymodbus version that could clash with the one Home
Assistant core ships for its own Modbus integration.

This module has no Home Assistant imports so it can be tested on its own.
"""

from __future__ import annotations

import asyncio
import struct

READ_HOLDING_REGISTERS = 0x03
WRITE_SINGLE_REGISTER = 0x06

EXCEPTION_NAMES = {
    1: "illegal function",
    2: "illegal data address",
    3: "illegal data value",
    4: "server device failure",
    6: "server device busy",
}


class ModbusError(Exception):
    """Base error for this client."""


class ModbusConnectionError(ModbusError):
    """Could not connect, or the connection dropped or timed out."""


class ModbusExceptionResponse(ModbusError):
    """The device answered with a Modbus exception code."""

    def __init__(self, function: int, code: int) -> None:
        self.function = function
        self.code = code
        name = EXCEPTION_NAMES.get(code, "unknown")
        super().__init__(f"Modbus exception {code} ({name}) for function {function:#04x}")


class ModbusTcpClient:
    """Single persistent Modbus TCP connection with request serialisation.

    Addresses are 0-based protocol addresses. Callers that work with the
    manual's 1-based register numbers subtract 1 before calling.
    """

    def __init__(
        self, host: str, port: int = 502, unit_id: int = 1, timeout: float = 5.0
    ) -> None:
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._transaction_id = 0
        self._lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    async def close(self) -> None:
        async with self._lock:
            await self._close()

    async def read_holding_registers(self, address: int, count: int) -> list[int]:
        async with self._lock:
            return await self._read(address, count)

    async def write_register(self, address: int, value: int) -> None:
        async with self._lock:
            await self._write(address, value)

    async def update_bits(self, address: int, mask: int, bits: int) -> int:
        """Read-modify-write the bits in ``mask`` of one register.

        Runs under a single lock so no other request can interleave between
        the read and the write. Returns the value written.
        """
        if not 0 <= mask <= 0xFFFF:
            raise ValueError("mask must be a 16-bit value")
        async with self._lock:
            (current,) = await self._read(address, 1)
            new = (current & ~mask & 0xFFFF) | (bits & mask)
            if new != current:
                await self._write(address, new)
            return new

    # Internal helpers, called with the lock held.

    async def _read(self, address: int, count: int) -> list[int]:
        if not 1 <= count <= 125:
            raise ValueError("count must be between 1 and 125")
        pdu = struct.pack(">BHH", READ_HOLDING_REGISTERS, address, count)
        response = await self._request(pdu)
        if len(response) < 2 or response[1] != 2 * count or len(response) != 2 + 2 * count:
            raise ModbusError(f"Malformed read response: {response.hex()}")
        return list(struct.unpack(f">{count}H", response[2:]))

    async def _write(self, address: int, value: int) -> None:
        if not 0 <= value <= 0xFFFF:
            raise ValueError("value must be a 16-bit unsigned integer")
        pdu = struct.pack(">BHH", WRITE_SINGLE_REGISTER, address, value)
        response = await self._request(pdu)
        if response != pdu:
            raise ModbusError(f"Unexpected write echo: {response.hex()}")

    async def _request(self, pdu: bytes) -> bytes:
        """Send one PDU and return the response PDU, retrying once on a stale connection."""
        for attempt in (1, 2):
            try:
                await self._ensure_connected()
                return await asyncio.wait_for(self._exchange(pdu), self.timeout)
            except ModbusExceptionResponse:
                raise
            except (TimeoutError, OSError, asyncio.IncompleteReadError, ModbusConnectionError) as err:
                await self._close()
                if attempt == 2:
                    raise ModbusConnectionError(
                        f"Communication with {self.host}:{self.port} failed: {err!r}"
                    ) from err
        raise AssertionError("unreachable")

    async def _exchange(self, pdu: bytes) -> bytes:
        assert self._reader is not None and self._writer is not None
        self._transaction_id = (self._transaction_id + 1) & 0xFFFF
        tid = self._transaction_id
        header = struct.pack(">HHHB", tid, 0, len(pdu) + 1, self.unit_id)
        self._writer.write(header + pdu)
        await self._writer.drain()

        while True:
            mbap = await self._reader.readexactly(7)
            r_tid, protocol, length, _unit = struct.unpack(">HHHB", mbap)
            if protocol != 0 or not 2 <= length <= 254:
                raise ModbusConnectionError(f"Invalid MBAP header: {mbap.hex()}")
            body = await self._reader.readexactly(length - 1)
            if r_tid == tid:
                break
            # A late answer to an earlier, timed-out request: skip it.

        function = body[0]
        if function == pdu[0] | 0x80:
            raise ModbusExceptionResponse(pdu[0], body[1] if len(body) > 1 else 0)
        if function != pdu[0]:
            raise ModbusError(f"Unexpected function code {function:#04x}")
        return body

    async def _ensure_connected(self) -> None:
        if self.connected:
            return
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), self.timeout
            )
        except (TimeoutError, OSError) as err:
            self._reader = self._writer = None
            raise ModbusConnectionError(
                f"Cannot connect to {self.host}:{self.port}: {err!r}"
            ) from err

    async def _close(self) -> None:
        writer, self._reader, self._writer = self._writer, None, None
        if writer is None:
            return
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), 1)
        except (TimeoutError, OSError):
            pass
