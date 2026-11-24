"""Register map and decoding for the Efilos "Controlador TS" (IP version).

Register numbers here are the 1-based numbers printed in the Efilos manual
(TABELA MODBUS, pages 17-19). The protocol address is ``register - 1``.

No Home Assistant imports, so this can be unit tested on its own.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

# Blocks read on every poll: (first register, count). Every register in
# these ranges is defined in the manual's table.
POLL_BLOCKS: tuple[tuple[int, int], ...] = (
    (20, 1),   # parameter flags
    (51, 6),   # speed / temperature / timer / remote / humidity / free set-points
    (81, 20),  # unit 1 data: temperatures, status, fan speeds, alarms, hours
)

# Read once at setup.
REG_SW_VERSION_0 = 3   # AAMM
REG_SW_VERSION_1 = 4   # DDPP
REG_CONFIG_7 = 7       # B08 FANS_FAIL_TACH: documented as the rpm flag, unreliable in practice

# Configuration
REG_PARAMETER_FLAGS = 20
# Commands
REG_SPEED_SET_POINT = 51
# Unit 1 data
REG_TEMP_OUTDOOR = 81   # TEMP_E
REG_TEMP_EXTRACT = 82   # TEMP_R, air coming from the rooms
REG_TEMP_EXHAUST = 83   # TEMP_X, air expelled outside
REG_TEMP_SUPPLY = 84    # TEMP_I, air blown into the rooms
REG_TEMP_WATER = 85     # TEMP_W
REG_STATUS_FLAGS = 86
REG_SPEED_SUPPLY = 87
REG_SPEED_EXHAUST = 88
REG_AUTO_INPUT = 89
REG_ALARMS_1 = 90
REG_PRESSURE_SUPPLY = 91
REG_PRESSURE_EXHAUST = 92
REG_FLOW_SUPPLY = 93
REG_FLOW_EXHAUST = 94
REG_FAN_HOURS_HIGH = 95
REG_FAN_HOURS_LOW = 96
REG_ALARMS_2 = 97
REG_PRE_HEAT = 98
REG_POST_HEAT = 99
REG_TEMP_DEHUMIDIFIER = 100

# Register 20 bits
FLAG_SEASON_MASK = 0b0000_0011
FLAG_BYPASS_MASK = 0b0000_1100
FLAG_BYPASS_SHIFT = 2
FLAG_DEHUMIDIFIER_OFF = 1 << 4
FLAG_FANS_OFF = 1 << 5
FLAG_POST_TREATMENT_OFF = 1 << 6

SEASONS = ("auto", "winter", "summer")
BYPASS_MODES = ("auto", "closed", "open")

# Register 51 special values
SPEED_OFF = 0
VARIABLE_SPEED_SCHEDULE = 101
VARIABLE_SPEED_AUTO = 102
THREE_SPEED_SCHEDULE = 4
THREE_SPEED_AUTO = 5

# Register 86 bits
STATUS_BYPASS_OPEN = 1 << 0
STATUS_SUPPLY_REMOTE = 1 << 1
STATUS_EXHAUST_REMOTE = 1 << 2
STATUS_DEHUMIDIFY = 1 << 3
STATUS_ANTIFROST = 1 << 4
STATUS_HEAT_1 = 1 << 8
STATUS_HEAT_2 = 1 << 9

ALARM_1_BITS: dict[int, str] = {
    0: "comm_x540",
    1: "outdoor_probe",
    2: "extract_probe",
    3: "exhaust_probe",
    4: "filters",
    5: "fans",
    6: "air_quality_sensor",
    7: "supply_probe",
    8: "comm_x531",
    9: "water_probe",
    10: "water_coil_frost",
    11: "air_quality_timeout",
    12: "comm_x570_supply",
    13: "comm_x570_exhaust",
    14: "supply_pressure_sensor",
    15: "exhaust_pressure_sensor",
}

ALARM_2_BITS: dict[int, str] = {
    0: "configuration",
    1: "anti_ice",
    2: "analog_input_2",
    3: "dewpoint_probe",
    4: "comm_x570_extra_supply",
    5: "comm_x570_extra_exhaust",
    6: "x570_extra_supply",
    7: "x570_extra_exhaust",
    8: "air_quality_2_timeout",
    # B09 MIN_SPEED is a status (unit forced to min speed by a digital
    # input), not a fault, so it is not treated as an alarm.
}

ALARM_1_FILTERS = 1 << 4
ALARM_1_FANS = 1 << 5

# Temperature values outside this range are treated as "no probe".
_TEMP_MIN = -50.0
_TEMP_MAX = 100.0


def signed16(value: int) -> int:
    return value - 0x10000 if value >= 0x8000 else value


def decode_temperature(raw: int | None) -> float | None:
    if raw is None:
        return None
    value = signed16(raw) / 10
    if not _TEMP_MIN <= value <= _TEMP_MAX:
        return None
    return value


def set_bits(current: int, mask: int, bits: int) -> int:
    return (current & ~mask & 0xFFFF) | (bits & mask)


@dataclass
class VmcData:
    """One poll's worth of registers, keyed by the manual's register number."""

    registers: dict[int, int] = field(default_factory=dict)

    @classmethod
    def from_blocks(cls, blocks: Mapping[int, list[int]]) -> VmcData:
        registers: dict[int, int] = {}
        for start, values in blocks.items():
            for offset, value in enumerate(values):
                registers[start + offset] = value
        return cls(registers)

    def get(self, register: int) -> int | None:
        return self.registers.get(register)

    # Parameter flags (register 20)

    @property
    def parameter_flags(self) -> int | None:
        return self.get(REG_PARAMETER_FLAGS)

    @property
    def fans_on(self) -> bool | None:
        flags = self.parameter_flags
        return None if flags is None else not flags & FLAG_FANS_OFF

    @property
    def season(self) -> str | None:
        flags = self.parameter_flags
        if flags is None:
            return None
        index = flags & FLAG_SEASON_MASK
        return SEASONS[index] if index < len(SEASONS) else None

    @property
    def bypass_mode(self) -> str | None:
        flags = self.parameter_flags
        if flags is None:
            return None
        index = (flags & FLAG_BYPASS_MASK) >> FLAG_BYPASS_SHIFT
        return BYPASS_MODES[index] if index < len(BYPASS_MODES) else None

    # Commands

    @property
    def speed_set_point(self) -> int | None:
        return self.get(REG_SPEED_SET_POINT)

    # Unit 1 data

    def temperature(self, register: int) -> float | None:
        return decode_temperature(self.get(register))

    @property
    def status_flags(self) -> int | None:
        return self.get(REG_STATUS_FLAGS)

    def status(self, bit_mask: int) -> bool | None:
        flags = self.status_flags
        return None if flags is None else bool(flags & bit_mask)

    @property
    def fan_hours(self) -> int | None:
        high = self.get(REG_FAN_HOURS_HIGH)
        low = self.get(REG_FAN_HOURS_LOW)
        if high is None or low is None:
            return None
        return (high << 16) | low

    @property
    def alarms_1(self) -> int | None:
        return self.get(REG_ALARMS_1)

    @property
    def alarms_2(self) -> int | None:
        return self.get(REG_ALARMS_2)

    def alarm_1(self, bit_mask: int) -> bool | None:
        alarms = self.alarms_1
        return None if alarms is None else bool(alarms & bit_mask)

    @property
    def active_alarms(self) -> list[str]:
        """Names of every active fault in registers 90 and 97."""
        active: list[str] = []
        for value, names in ((self.alarms_1, ALARM_1_BITS), (self.alarms_2, ALARM_2_BITS)):
            if value is None:
                continue
            active.extend(name for bit, name in names.items() if value & (1 << bit))
        return active

    @property
    def general_alarm(self) -> bool | None:
        """Any fault other than the filter alarm, which has its own entity."""
        if self.alarms_1 is None and self.alarms_2 is None:
            return None
        return any(name != "filters" for name in self.active_alarms)


def format_software_version(ver0: int | None, ver1: int | None) -> str | None:
    """Registers 3 and 4 hold the version as AAMM and DDPP, one BCD digit per nibble."""
    if ver0 is None or ver1 is None:
        return None
    return f"{ver0:04X}.{ver1:04X}"
