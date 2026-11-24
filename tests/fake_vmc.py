"""A tiny Modbus TCP server that behaves like the Efilos TS IP controller.

Only function codes 03 and 06 are implemented. Reading or writing a
register that isn't defined returns exception 2 (illegal data address),
which is how a strict device would react.
"""

from __future__ import annotations

import asyncio
import struct

# Values read from a real Air Compact 415 Lite on 2026-11-18, keyed by the
# manual's 1-based register number. Everything else in the published
# ranges is 0.
REAL_UNIT_VALUES = {
    3: 0x2501,  # firmware 2501.0900, read as 9473 / 2304
    4: 0x0900,
    7: 0,       # rpm flag (B08) clear even though the fans report rpm
    20: 1,      # winter, bypass auto, fans on
    51: 35,     # 35 %
    81: 166,    # 16.6 °C outdoor
    82: 194,    # 19.4 °C extract
    83: 181,    # 18.1 °C exhaust
    84: 196,    # 19.6 °C supply
    87: 1469,   # rpm
    88: 1500,   # rpm
    95: 0,
    96: 4321,   # fan hours
}

DEFINED_RANGES = ((1, 5), (14, 14), (20, 20), (24, 27), (51, 56), (81, 100))


class FakeVmc:
    def __init__(self, values: dict[int, int] | None = None) -> None:
        self.registers: dict[int, int] = {}
        for first, last in DEFINED_RANGES:
            for register in range(first, last + 1):
                self.registers[register] = 0
        self.registers.update(REAL_UNIT_VALUES if values is None else values)
        self.writes: list[tuple[int, int]] = []
        self.port = 0
        self._server: asyncio.Server | None = None
        self._clients: set[asyncio.StreamWriter] = set()

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        await self.drop_clients()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    async def drop_clients(self) -> None:
        """Close every open connection, like the device does after its timeout."""
        for writer in list(self._clients):
            writer.close()
        self._clients.clear()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._clients.add(writer)
        try:
            while True:
                header = await reader.readexactly(7)
                tid, _proto, length, unit = struct.unpack(">HHHB", header)
                pdu = await reader.readexactly(length - 1)
                response = self._process(pdu)
                writer.write(struct.pack(">HHHB", tid, 0, len(response) + 1, unit) + response)
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            self._clients.discard(writer)
            writer.close()

    def _process(self, pdu: bytes) -> bytes:
        function = pdu[0]
        if function == 0x03:
            address, count = struct.unpack(">HH", pdu[1:5])
            registers = range(address + 1, address + 1 + count)
            if any(r not in self.registers for r in registers):
                return bytes([function | 0x80, 2])
            values = [self.registers[r] for r in registers]
            return bytes([function, 2 * count]) + struct.pack(f">{count}H", *values)
        if function == 0x06:
            address, value = struct.unpack(">HH", pdu[1:5])
            register = address + 1
            if register not in self.registers:
                return bytes([function | 0x80, 2])
            self.registers[register] = value
            self.writes.append((register, value))
            return pdu
        return bytes([function | 0x80, 1])
