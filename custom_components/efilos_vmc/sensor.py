"""Sensors for the Efilos VMC."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    EntityCategory,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_FAN_FEEDBACK, FAN_FEEDBACK_RPM
from .coordinator import EfilosConfigEntry, EfilosCoordinator
from .entity import EfilosEntity
from .registers import (
    REG_AUTO_INPUT,
    REG_FLOW_EXHAUST,
    REG_FLOW_SUPPLY,
    REG_POST_HEAT,
    REG_PRE_HEAT,
    REG_PRESSURE_EXHAUST,
    REG_PRESSURE_SUPPLY,
    REG_SPEED_EXHAUST,
    REG_SPEED_SUPPLY,
    REG_TEMP_EXHAUST,
    REG_TEMP_EXTRACT,
    REG_TEMP_OUTDOOR,
    REG_TEMP_SUPPLY,
    REG_TEMP_WATER,
    VmcData,
)

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class EfilosSensorDescription(SensorEntityDescription):
    value_fn: Callable[[VmcData], float | int | None]


def _temperature(key: str, register: int, *, enabled: bool = True) -> EfilosSensorDescription:
    return EfilosSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_registry_enabled_default=enabled,
        value_fn=lambda data: data.temperature(register),
    )


def _raw(key: str, register: int, unit: str, *, device_class: SensorDeviceClass | None = None,
         enabled: bool = False) -> EfilosSensorDescription:
    return EfilosSensorDescription(
        key=key,
        translation_key=key,
        device_class=device_class,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=unit,
        entity_registry_enabled_default=enabled,
        value_fn=lambda data: data.get(register),
    )


SENSORS: tuple[EfilosSensorDescription, ...] = (
    _temperature("outdoor_temperature", REG_TEMP_OUTDOOR),
    _temperature("extract_temperature", REG_TEMP_EXTRACT),
    _temperature("exhaust_temperature", REG_TEMP_EXHAUST),
    _temperature("supply_temperature", REG_TEMP_SUPPLY),
    _temperature("water_temperature", REG_TEMP_WATER, enabled=False),
    _raw("air_quality_input", REG_AUTO_INPUT, PERCENTAGE),
    _raw("supply_pressure", REG_PRESSURE_SUPPLY, UnitOfPressure.PA, device_class=SensorDeviceClass.PRESSURE),
    _raw("exhaust_pressure", REG_PRESSURE_EXHAUST, UnitOfPressure.PA, device_class=SensorDeviceClass.PRESSURE),
    _raw("supply_airflow", REG_FLOW_SUPPLY, UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
         device_class=SensorDeviceClass.VOLUME_FLOW_RATE),
    _raw("exhaust_airflow", REG_FLOW_EXHAUST, UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
         device_class=SensorDeviceClass.VOLUME_FLOW_RATE),
    _raw("pre_heating", REG_PRE_HEAT, PERCENTAGE),
    _raw("post_heating", REG_POST_HEAT, PERCENTAGE),
    EfilosSensorDescription(
        key="fan_hours",
        translation_key="fan_hours",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.fan_hours,
    ),
)


def _fan_speed_sensors(feedback: str) -> tuple[EfilosSensorDescription, ...]:
    unit = REVOLUTIONS_PER_MINUTE if feedback == FAN_FEEDBACK_RPM else PERCENTAGE
    return tuple(
        EfilosSensorDescription(
            key=key,
            translation_key=key,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=unit,
            value_fn=lambda data, register=register: data.get(register),
        )
        for key, register in (
            ("supply_fan_speed", REG_SPEED_SUPPLY),
            ("exhaust_fan_speed", REG_SPEED_EXHAUST),
        )
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EfilosConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    descriptions = SENSORS + _fan_speed_sensors(
        entry.options.get(CONF_FAN_FEEDBACK, FAN_FEEDBACK_RPM)
    )
    async_add_entities(EfilosSensor(coordinator, description) for description in descriptions)


class EfilosSensor(EfilosEntity, SensorEntity):
    entity_description: EfilosSensorDescription

    def __init__(self, coordinator: EfilosCoordinator, description: EfilosSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | None:
        return self.entity_description.value_fn(self.coordinator.data)
