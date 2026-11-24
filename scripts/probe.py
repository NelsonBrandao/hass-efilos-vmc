"""Read-only connection check for an Efilos Controlador TS IP panel.

Usage: python3 -I scripts/probe.py <host> [port] [unit_id]

Uses the integration's own Modbus client and decoder without importing Home
Assistant, and never writes to the controller.
"""

import asyncio
import importlib.util
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent / "custom_components" / "efilos_vmc"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, PACKAGE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


modbus = _load("modbus")
registers = _load("registers")


async def main(host: str, port: int, unit_id: int) -> int:
    client = modbus.ModbusTcpClient(host, port, unit_id, timeout=5)
    blocks: dict[int, list[int]] = {}
    failed = False
    for start, count in registers.POLL_BLOCKS:
        try:
            blocks[start] = await client.read_holding_registers(start - 1, count)
            print(f"registers {start}-{start + count - 1}: OK {blocks[start]}")
        except modbus.ModbusError as err:
            failed = True
            print(f"registers {start}-{start + count - 1}: FAILED {err}")
    for register in (3, 4, 7):
        try:
            print(f"register {register}: {await client.read_holding_registers(register - 1, 1)}")
        except modbus.ModbusError as err:
            print(f"register {register}: {err}")
    await client.close()

    data = registers.VmcData.from_blocks(blocks)
    print(
        "decoded:",
        {
            "temperatures": [data.temperature(r) for r in (81, 82, 83, 84)],
            "fans_on": data.fans_on,
            "speed_set_point": data.speed_set_point,
            "season": data.season,
            "bypass": data.bypass_mode,
            "fan_hours": data.fan_hours,
            "alarms": data.active_alarms,
        },
    )
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(
        asyncio.run(
            main(
                sys.argv[1],
                int(sys.argv[2]) if len(sys.argv) > 2 else 502,
                int(sys.argv[3]) if len(sys.argv) > 3 else 1,
            )
        )
    )
