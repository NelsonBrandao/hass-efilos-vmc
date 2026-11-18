"""Binary sensors for the Efilos VMC."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import EfilosConfigEntry, EfilosCoordinator
from .entity import EfilosEntity
from .registers import (
    ALARM_1_FANS,
    ALARM_1_FILTERS,
    STATUS_ANTIFROST,
    STATUS_BYPASS_OPEN,
    VmcData,
)

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class EfilosBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[VmcData], bool | None]
    attributes_fn: Callable[[VmcData], dict[str, Any]] | None = None


BINARY_SENSORS: tuple[EfilosBinarySensorDescription, ...] = (
    EfilosBinarySensorDescription(
        key="bypass_open",
        translation_key="bypass_open",
        device_class=BinarySensorDeviceClass.OPENING,
        value_fn=lambda data: data.status(STATUS_BYPASS_OPEN),
    ),
    EfilosBinarySensorDescription(
        key="antifrost",
        translation_key="antifrost",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda data: data.status(STATUS_ANTIFROST),
    ),
    EfilosBinarySensorDescription(
        key="filter_alarm",
        translation_key="filter_alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.alarm_1(ALARM_1_FILTERS),
    ),
    EfilosBinarySensorDescription(
        key="fan_failure",
        translation_key="fan_failure",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.alarm_1(ALARM_1_FANS),
    ),
    EfilosBinarySensorDescription(
        key="alarm",
        translation_key="alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.general_alarm,
        attributes_fn=lambda data: {
            "active_alarms": data.active_alarms,
            "alarms_1": data.alarms_1,
            "alarms_2": data.alarms_2,
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EfilosConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        EfilosBinarySensor(coordinator, description) for description in BINARY_SENSORS
    )


class EfilosBinarySensor(EfilosEntity, BinarySensorEntity):
    entity_description: EfilosBinarySensorDescription

    def __init__(
        self, coordinator: EfilosCoordinator, description: EfilosBinarySensorDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(self.coordinator.data)
