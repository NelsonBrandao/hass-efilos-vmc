"""End-to-end entity tests against the fake controller."""

from __future__ import annotations

import pytest
from homeassistant.const import ATTR_ENTITY_ID, CONF_HOST, CONF_PORT, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.efilos_vmc.const import (
    CONF_FAN_FEEDBACK,
    CONF_SPEED_CONTROL,
    CONF_UNIT_ID,
    DOMAIN,
)

from .fake_vmc import FakeVmc


async def _setup(hass: HomeAssistant, fake_vmc: FakeVmc, speed_control: str = "variable") -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Efilos VMC",
        unique_id=f"127.0.0.1:{fake_vmc.port}:1",
        data={CONF_HOST: "127.0.0.1", CONF_PORT: fake_vmc.port, CONF_UNIT_ID: 1},
        options={CONF_SPEED_CONTROL: speed_control, CONF_FAN_FEEDBACK: "rpm"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _refresh(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


async def test_states_match_real_unit(hass: HomeAssistant, fake_vmc: FakeVmc) -> None:
    entry = await _setup(hass, fake_vmc)

    assert hass.states.get("sensor.efilos_vmc_outdoor_air_temperature").state == "16.6"
    assert hass.states.get("sensor.efilos_vmc_extract_air_temperature").state == "19.4"
    assert hass.states.get("sensor.efilos_vmc_exhaust_air_temperature").state == "18.1"
    assert hass.states.get("sensor.efilos_vmc_supply_air_temperature").state == "19.6"

    supply_speed = hass.states.get("sensor.efilos_vmc_supply_fan_speed")
    assert supply_speed.state == "1469"
    assert supply_speed.attributes["unit_of_measurement"] == "rpm"
    assert hass.states.get("sensor.efilos_vmc_fan_running_hours").state == "4321"

    fan = hass.states.get("fan.efilos_vmc")
    assert fan.state == STATE_ON
    assert fan.attributes["percentage"] == 35
    assert fan.attributes["preset_mode"] is None

    assert hass.states.get("select.efilos_vmc_season").state == "winter"
    assert hass.states.get("select.efilos_vmc_bypass").state == "auto"
    assert hass.states.get("binary_sensor.efilos_vmc_filter_alarm").state == STATE_OFF
    assert hass.states.get("binary_sensor.efilos_vmc_alarm").state == STATE_OFF
    assert hass.states.get("binary_sensor.efilos_vmc_bypass_open").state == STATE_OFF

    # Optional sensors are disabled by default.
    assert hass.states.get("sensor.efilos_vmc_supply_airflow") is None

    device = entry.runtime_data
    assert device.software_version == "2501.0900"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_fan_controls(hass: HomeAssistant, fake_vmc: FakeVmc) -> None:
    entry = await _setup(hass, fake_vmc)
    target = {ATTR_ENTITY_ID: "fan.efilos_vmc"}

    await hass.services.async_call("fan", "set_percentage", {**target, "percentage": 60}, blocking=True)
    assert fake_vmc.registers[51] == 60
    assert fake_vmc.registers[20] == 1  # season bits untouched, fans still on

    await hass.services.async_call("fan", "turn_off", target, blocking=True)
    assert fake_vmc.registers[20] == 1 | (1 << 5)
    await _refresh(hass, entry)
    assert hass.states.get("fan.efilos_vmc").state == STATE_OFF

    await hass.services.async_call("fan", "set_preset_mode", {**target, "preset_mode": "auto"}, blocking=True)
    assert fake_vmc.registers[51] == 102
    assert fake_vmc.registers[20] == 1
    await _refresh(hass, entry)
    fan = hass.states.get("fan.efilos_vmc")
    assert fan.state == STATE_ON
    assert fan.attributes["preset_mode"] == "auto"
    assert fan.attributes["percentage"] is None

    await hass.services.async_call("fan", "set_percentage", {**target, "percentage": 0}, blocking=True)
    assert fake_vmc.registers[20] & (1 << 5)
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_three_speed_fan(hass: HomeAssistant, fake_vmc: FakeVmc) -> None:
    fake_vmc.registers[51] = 2
    entry = await _setup(hass, fake_vmc, speed_control="three_speed")
    fan = hass.states.get("fan.efilos_vmc")
    assert fan.attributes["percentage"] == 66
    assert fan.attributes["percentage_step"] == pytest.approx(100 / 3)

    await hass.services.async_call(
        "fan", "set_percentage", {ATTR_ENTITY_ID: "fan.efilos_vmc", "percentage": 100}, blocking=True
    )
    assert fake_vmc.registers[51] == 3
    await hass.services.async_call(
        "fan", "set_preset_mode", {ATTR_ENTITY_ID: "fan.efilos_vmc", "preset_mode": "schedule"}, blocking=True
    )
    assert fake_vmc.registers[51] == 4
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_selects_change_only_their_bits(hass: HomeAssistant, fake_vmc: FakeVmc) -> None:
    fake_vmc.registers[20] = 1 | (1 << 6)  # winter, post-treatment off
    entry = await _setup(hass, fake_vmc)

    await hass.services.async_call(
        "select", "select_option", {ATTR_ENTITY_ID: "select.efilos_vmc_bypass", "option": "open"}, blocking=True
    )
    assert fake_vmc.registers[20] == 1 | (2 << 2) | (1 << 6)

    await hass.services.async_call(
        "select", "select_option", {ATTR_ENTITY_ID: "select.efilos_vmc_season", "option": "summer"}, blocking=True
    )
    assert fake_vmc.registers[20] == 2 | (2 << 2) | (1 << 6)
    await _refresh(hass, entry)
    assert hass.states.get("select.efilos_vmc_bypass").state == "open"
    assert hass.states.get("select.efilos_vmc_season").state == "summer"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_alarms(hass: HomeAssistant, fake_vmc: FakeVmc) -> None:
    fake_vmc.registers[90] = (1 << 4) | (1 << 1)  # filters + outdoor probe
    entry = await _setup(hass, fake_vmc)
    assert hass.states.get("binary_sensor.efilos_vmc_filter_alarm").state == STATE_ON
    alarm = hass.states.get("binary_sensor.efilos_vmc_alarm")
    assert alarm.state == STATE_ON
    assert alarm.attributes["active_alarms"] == ["outdoor_probe", "filters"]
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_unavailable_when_device_goes_away(hass: HomeAssistant, fake_vmc: FakeVmc) -> None:
    entry = await _setup(hass, fake_vmc)
    await fake_vmc.stop()
    await _refresh(hass, entry)
    assert hass.states.get("fan.efilos_vmc").state == "unavailable"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_block_read_rejected_falls_back(hass: HomeAssistant, fake_vmc: FakeVmc) -> None:
    # A firmware that doesn't define register 85 rejects the whole 81-100 block.
    del fake_vmc.registers[85]
    entry = await _setup(hass, fake_vmc)
    assert hass.states.get("sensor.efilos_vmc_outdoor_air_temperature").state == "16.6"
    assert hass.states.get("fan.efilos_vmc").attributes["percentage"] == 35
    assert await hass.config_entries.async_unload(entry.entry_id)
