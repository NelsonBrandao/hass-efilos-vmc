"""Fan entity for the Efilos VMC.

On/off uses bit 5 of register 20 ("speed switch off"). Speed and the
schedule/auto presets use register 51, whose encoding depends on the motor
type configured in the options.
"""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from .const import (
    CONF_SPEED_CONTROL,
    PRESET_AUTO,
    PRESET_SCHEDULE,
    SPEED_CONTROL_THREE_SPEED,
    SPEED_CONTROL_VARIABLE,
)
from .coordinator import EfilosConfigEntry, EfilosCoordinator
from .entity import EfilosEntity
from .registers import (
    FLAG_FANS_OFF,
    REG_PARAMETER_FLAGS,
    REG_SPEED_SET_POINT,
    THREE_SPEED_AUTO,
    THREE_SPEED_SCHEDULE,
    VARIABLE_SPEED_AUTO,
    VARIABLE_SPEED_SCHEDULE,
)

PARALLEL_UPDATES = 1

THREE_SPEED_RANGE = (1, 3)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EfilosConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    speed_control = entry.options.get(CONF_SPEED_CONTROL, SPEED_CONTROL_VARIABLE)
    async_add_entities([EfilosFan(entry.runtime_data, speed_control)])


class EfilosFan(EfilosEntity, FanEntity):
    _attr_name = None  # main feature: the entity takes the device name
    _attr_translation_key = "vmc"
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    def __init__(self, coordinator: EfilosCoordinator, speed_control: str) -> None:
        super().__init__(coordinator, "fan")
        self._attr_preset_modes = [PRESET_SCHEDULE, PRESET_AUTO]
        self._three_speed = speed_control == SPEED_CONTROL_THREE_SPEED
        if self._three_speed:
            self._presets = {PRESET_SCHEDULE: THREE_SPEED_SCHEDULE, PRESET_AUTO: THREE_SPEED_AUTO}
            self._attr_speed_count = 3
        else:
            self._presets = {
                PRESET_SCHEDULE: VARIABLE_SPEED_SCHEDULE,
                PRESET_AUTO: VARIABLE_SPEED_AUTO,
            }
            self._attr_speed_count = 100

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.fans_on

    @property
    def percentage(self) -> int | None:
        set_point = self.coordinator.data.speed_set_point
        if set_point is None or set_point in self._presets.values():
            return None
        if self._three_speed:
            if not THREE_SPEED_RANGE[0] <= set_point <= THREE_SPEED_RANGE[1]:
                return None
            return ranged_value_to_percentage(THREE_SPEED_RANGE, set_point)
        return set_point if 0 <= set_point <= 100 else None

    @property
    def preset_mode(self) -> str | None:
        set_point = self.coordinator.data.speed_set_point
        for preset, value in self._presets.items():
            if set_point == value:
                return preset
        return None

    def _set_point_for(self, percentage: int) -> int:
        if self._three_speed:
            return math.ceil(percentage_to_ranged_value(THREE_SPEED_RANGE, percentage))
        return max(1, min(100, percentage))

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            await self.async_turn_off()
            return
        await self.coordinator.async_write_register(
            REG_SPEED_SET_POINT, self._set_point_for(percentage)
        )
        await self._set_fans_on(True)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self.coordinator.async_write_register(
            REG_SPEED_SET_POINT, self._presets[preset_mode]
        )
        await self._set_fans_on(True)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            await self._set_fans_on(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set_fans_on(False)

    async def _set_fans_on(self, on: bool) -> None:
        await self.coordinator.async_update_bits(
            REG_PARAMETER_FLAGS, FLAG_FANS_OFF, 0 if on else FLAG_FANS_OFF
        )
