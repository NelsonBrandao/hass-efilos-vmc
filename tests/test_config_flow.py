"""Tests for the config and options flows."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.efilos_vmc.const import (
    CONF_FAN_FEEDBACK,
    CONF_SPEED_CONTROL,
    CONF_UNIT_ID,
    DOMAIN,
)
from homeassistant import config_entries

from .fake_vmc import FakeVmc


async def test_user_flow(hass: HomeAssistant, fake_vmc: FakeVmc) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "127.0.0.1", CONF_PORT: fake_vmc.port, CONF_UNIT_ID: 1},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "fans"
    # Register 7 isn't readable on the fake, so the 1469 reading decides: rpm.
    schema_defaults = {
        str(key): key.default() for key in result["data_schema"].schema if hasattr(key, "default")
    }
    assert schema_defaults[CONF_FAN_FEEDBACK] == "rpm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SPEED_CONTROL: "variable", CONF_FAN_FEEDBACK: "rpm"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Efilos VMC"
    assert result["data"] == {CONF_HOST: "127.0.0.1", CONF_PORT: fake_vmc.port, CONF_UNIT_ID: 1}
    assert result["options"] == {CONF_SPEED_CONTROL: "variable", CONF_FAN_FEEDBACK: "rpm"}
    await hass.async_block_till_done()

    entry = result["result"]
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_user_flow_cannot_connect(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "127.0.0.1", CONF_PORT: 1, CONF_UNIT_ID: 1}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_already_configured(hass: HomeAssistant, fake_vmc: FakeVmc) -> None:
    MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"127.0.0.1:{fake_vmc.port}:1",
        data={CONF_HOST: "127.0.0.1", CONF_PORT: fake_vmc.port, CONF_UNIT_ID: 1},
    ).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "127.0.0.1", CONF_PORT: fake_vmc.port, CONF_UNIT_ID: 1},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(hass: HomeAssistant, fake_vmc: FakeVmc) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Efilos VMC",
        unique_id=f"127.0.0.1:{fake_vmc.port}:1",
        data={CONF_HOST: "127.0.0.1", CONF_PORT: fake_vmc.port, CONF_UNIT_ID: 1},
        options={CONF_SPEED_CONTROL: "variable", CONF_FAN_FEEDBACK: "rpm"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SPEED_CONTROL: "three_speed", CONF_FAN_FEEDBACK: "percent"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options == {CONF_SPEED_CONTROL: "three_speed", CONF_FAN_FEEDBACK: "percent"}
    assert hass.states.get("sensor.efilos_vmc_supply_fan_speed").attributes[
        "unit_of_measurement"
    ] == "%"
    assert await hass.config_entries.async_unload(entry.entry_id)
