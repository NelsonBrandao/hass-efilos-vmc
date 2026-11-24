"""Season and bypass selects for the Efilos VMC (register 20)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import EfilosConfigEntry, EfilosCoordinator
from .entity import EfilosEntity
from .registers import (
    FLAG_BYPASS_MASK,
    FLAG_BYPASS_SHIFT,
    FLAG_SEASON_MASK,
    REG_PARAMETER_FLAGS,
    VmcData,
)

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class EfilosSelectDescription(SelectEntityDescription):
    value_fn: Callable[[VmcData], str | None]
    values: dict[str, int]
    mask: int
    shift: int


SELECTS: tuple[EfilosSelectDescription, ...] = (
    EfilosSelectDescription(
        key="season",
        translation_key="season",
        # The register also allows 0 (auto), but the panels seen so far only offer winter and summer.
        values={"winter": 1, "summer": 2},
        options=["winter", "summer"],
        value_fn=lambda data: data.season,
        mask=FLAG_SEASON_MASK,
        shift=0,
    ),
    EfilosSelectDescription(
        key="bypass_mode",
        translation_key="bypass_mode",
        values={"auto": 0, "closed": 1, "open": 2},
        options=["auto", "closed", "open"],
        value_fn=lambda data: data.bypass_mode,
        mask=FLAG_BYPASS_MASK,
        shift=FLAG_BYPASS_SHIFT,
        # The Air Compact 415 Lite ignores this and drives the bypass from the season.
        entity_registry_enabled_default=False,
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
        value = self.entity_description.value_fn(self.coordinator.data)
        return value if value in self.entity_description.values else None

    async def async_select_option(self, option: str) -> None:
        description = self.entity_description
        await self.coordinator.async_update_bits(
            REG_PARAMETER_FLAGS, description.mask, description.values[option] << description.shift
        )
