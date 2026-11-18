"""Shared fixtures."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

from .fake_vmc import FakeVmc


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components/ in every test."""
    yield


@pytest.fixture(autouse=True)
def allow_localhost_sockets(socket_enabled):
    """The tests talk Modbus TCP to a fake controller on 127.0.0.1."""
    yield


@pytest.fixture
async def fake_vmc() -> AsyncGenerator[FakeVmc]:
    server = FakeVmc()
    await server.start()
    yield server
    await server.stop()
