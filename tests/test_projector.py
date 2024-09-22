"""Tests for projector module."""

from unittest.mock import AsyncMock

import pytest

from jvcprojector import command, const
from jvcprojector.error import JvcProjectorError
from jvcprojector.projector import JvcProjector

from . import HOST, IP, MAC, MODEL, PORT


@pytest.mark.asyncio
async def test_init(dev: AsyncMock):
    """Test init succeeds."""
    p = JvcProjector(IP, port=PORT)
    assert p.host == IP
    assert p.port == PORT
    with pytest.raises(JvcProjectorError):
        assert p.ip
    with pytest.raises(JvcProjectorError):
        assert p.model
    with pytest.raises(JvcProjectorError):
        assert p.mac


@pytest.mark.asyncio
async def test_connect(dev: AsyncMock):
    """Test connect succeeds."""
    p = JvcProjector(IP, port=PORT)
    await p.connect()
    assert p.ip == IP
    await p.disconnect()
    assert dev.disconnect.call_count == 1


@pytest.mark.asyncio
async def test_connect_host(dev: AsyncMock):
    """Test connect succeeds."""
    p = JvcProjector(HOST, port=PORT)
    await p.connect()
    assert p.ip == IP
    await p.disconnect()
    assert dev.disconnect.call_count == 1


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
    with pytest.raises(JvcProjectorError):
        await p.get_info()


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
        "input": const.HDMI1,
        "source": const.SIGNAL,
    }
