"""Bypass and season selects for the Efilos VMC (register 20)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import EfilosConfigEntry, EfilosCoordinator
from .entity import EfilosEntity
from .registers import (
    BYPASS_MODES,
    FLAG_BYPASS_MASK,
    FLAG_BYPASS_SHIFT,
    FLAG_SEASON_MASK,
    REG_PARAMETER_FLAGS,
    SEASONS,
    VmcData,
)

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class EfilosSelectDescription(SelectEntityDescription):
    value_fn: Callable[[VmcData], str | None]
    mask: int
    shift: int


SELECTS: tuple[EfilosSelectDescription, ...] = (
    EfilosSelectDescription(
        key="bypass_mode",
        translation_key="bypass_mode",
        options=list(BYPASS_MODES),
        value_fn=lambda data: data.bypass_mode,
        mask=FLAG_BYPASS_MASK,
        shift=FLAG_BYPASS_SHIFT,
    ),
    EfilosSelectDescription(
        key="season",
        translation_key="season",
        options=list(SEASONS),
        value_fn=lambda data: data.season,
        mask=FLAG_SEASON_MASK,
        shift=0,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EfilosConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(EfilosSelect(coordinator, description) for description in SELECTS)


class EfilosSelect(EfilosEntity, SelectEntity):
    entity_description: EfilosSelectDescription

    def __init__(self, coordinator: EfilosCoordinator, description: EfilosSelectDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def current_option(self) -> str | None:
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_select_option(self, option: str) -> None:
        description = self.entity_description
        index = description.options.index(option)
        await self.coordinator.async_update_bits(
            REG_PARAMETER_FLAGS, description.mask, index << description.shift
        )
