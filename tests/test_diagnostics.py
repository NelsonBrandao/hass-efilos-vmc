"""Tests for the diagnostics download."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.efilos_vmc.const import (
    CONF_FAN_FEEDBACK,
    CONF_SPEED_CONTROL,
    CONF_UNIT_ID,
    DOMAIN,
)
from custom_components.efilos_vmc.diagnostics import async_get_config_entry_diagnostics

from .fake_vmc import FakeVmc


async def test_diagnostics(hass: HomeAssistant, fake_vmc: FakeVmc) -> None:
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

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["entry"]["data"][CONF_HOST] == "**REDACTED**"
    assert result["entry"]["options"] == {CONF_SPEED_CONTROL: "variable", CONF_FAN_FEEDBACK: "rpm"}
    assert result["software_version"] == "2501.0900"
    assert result["decoded"]["speed_set_point"] == 35
    assert result["decoded"]["season"] == "winter"
    assert result["decoded"]["temperatures"]["81"] == 16.6
    assert result["registers"]["51"] == 35
    assert result["registers"]["87"] == 1469
    assert result["registers"]["6"] == "exception 2"  # not defined on the fake
    assert await hass.config_entries.async_unload(entry.entry_id)
