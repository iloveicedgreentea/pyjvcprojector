"""Tests for projector module."""

import hashlib
from unittest.mock import AsyncMock

import pytest

from jvcprojector import command, const
from jvcprojector.projector import JvcProjector

from . import IP, MAC, MODEL, PORT


@pytest.mark.asyncio
async def test_connect(dev: AsyncMock):
    """Test connect succeeds."""
    p = JvcProjector(IP, port=PORT)
    await p.connect()
    assert p.host == IP
    assert p.ip == IP
    assert p.port == PORT
    await p.disconnect()


@pytest.mark.asyncio
@pytest.mark.parametrize("dev", [{command.MODEL: None}], indirect=True)
async def test_unknown_model(dev: AsyncMock):
    """Test projector with unknown model succeeds."""
    p = JvcProjector(IP)
    await p.connect()
    await p.get_info()
    assert p.mac == MAC
    assert p.model == "(unknown)"


@pytest.mark.asyncio
@pytest.mark.parametrize("dev", [{command.MAC: None}], indirect=True)
async def test_unknown_mac(dev: AsyncMock):
    """Test projector with unknown mac uses model succeeds."""
    p = JvcProjector(IP)
    await p.connect()
    await p.get_info()
    assert p.mac == hashlib.md5(MODEL.encode()).digest().hex().encode()[0:12].decode()
    assert p.model == MODEL


@pytest.mark.asyncio
async def test_get_info(dev: AsyncMock):
    """Test get_info succeeds."""
    p = JvcProjector(IP)
    await p.connect()
    assert await p.get_info() == {"model": MODEL, "mac": MAC}


@pytest.mark.asyncio
async def test_get_state(dev: AsyncMock):
    """Test get_state succeeds."""
    p = JvcProjector(IP)
    await p.connect()
    assert await p.get_state() == {
        "power": const.ON,
        "input": const.INPUT_HDMI1,
        "source": const.SIGNAL,
    }
