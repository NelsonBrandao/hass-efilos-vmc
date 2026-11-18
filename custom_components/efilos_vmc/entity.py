"""Base entity for the Efilos VMC."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import EfilosCoordinator


class EfilosEntity(CoordinatorEntity[EfilosCoordinator]):
    """Common device info and unique IDs."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EfilosCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=coordinator.software_version,
        )
