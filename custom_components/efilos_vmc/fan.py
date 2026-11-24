"""Fan entity for the Efilos VMC.

Speed, presets and on/off all go through register 51. Writing 0 turns the
fans off, as the manual describes for a speed below the unit's minimum; the
"fans off" bit in register 20 is ignored by at least the Air Compact 415 Lite.
"""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from .const import (
    CONF_AUTO_PRESET,
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
    SPEED_OFF,
    THREE_SPEED_AUTO,
    THREE_SPEED_SCHEDULE,
    VARIABLE_SPEED_AUTO,
    VARIABLE_SPEED_SCHEDULE,
)

PARALLEL_UPDATES = 1

THREE_SPEED_RANGE = (1, 3)
DEFAULT_VARIABLE_SPEED = 50
DEFAULT_THREE_SPEED = 2


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EfilosConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(
        [
            EfilosFan(
                entry.runtime_data,
                entry.options.get(CONF_SPEED_CONTROL, SPEED_CONTROL_VARIABLE),
                entry.options.get(CONF_AUTO_PRESET, False),
            )
        ]
    )


class EfilosFan(EfilosEntity, FanEntity):
    _attr_name = None  # main feature: the entity takes the device name
    _attr_translation_key = "vmc"
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: EfilosCoordinator, speed_control: str, auto_preset: bool) -> None:
        super().__init__(coordinator, "fan")
        self._three_speed = speed_control == SPEED_CONTROL_THREE_SPEED
        if self._three_speed:
            self._attr_speed_count = 3
            presets = {PRESET_SCHEDULE: THREE_SPEED_SCHEDULE, PRESET_AUTO: THREE_SPEED_AUTO}
            self._last_on_set_point = DEFAULT_THREE_SPEED
        else:
            self._attr_speed_count = 100
            presets = {PRESET_SCHEDULE: VARIABLE_SPEED_SCHEDULE, PRESET_AUTO: VARIABLE_SPEED_AUTO}
            self._last_on_set_point = DEFAULT_VARIABLE_SPEED
        # Auto follows an air-quality or humidity sensor; without one the unit ignores it.
        if not auto_preset:
            del presets[PRESET_AUTO]
        self._presets = presets
        self._attr_preset_modes = list(presets)
        self._remember_set_point()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._remember_set_point()
        super()._handle_coordinator_update()

    def _remember_set_point(self) -> None:
        """Keep the last running speed or preset so turning on can restore it."""
        data = self.coordinator.data
        set_point = data.speed_set_point if data else None
        if set_point:
            self._last_on_set_point = set_point

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if data.speed_set_point is None:
            return None
        return data.speed_set_point != SPEED_OFF and data.fans_on is not False

    @property
    def percentage(self) -> int | None:
        set_point = self.coordinator.data.speed_set_point
        if set_point is None or set_point in self._presets.values():
            return None
        if set_point == SPEED_OFF:
            return 0
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
        await self._run(self._set_point_for(percentage))

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self._run(self._presets[preset_mode])

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
            await self._run(self._last_on_set_point)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._remember_set_point()
        await self.coordinator.async_write_register(REG_SPEED_SET_POINT, SPEED_OFF)

    async def _run(self, set_point: int) -> None:
        await self.coordinator.async_write_register(REG_SPEED_SET_POINT, set_point)
        # Units that honour the "fans off" bit would stay off with it set.
        if self.coordinator.data.fans_on is False:
            await self.coordinator.async_update_bits(REG_PARAMETER_FLAGS, FLAG_FANS_OFF, 0)
