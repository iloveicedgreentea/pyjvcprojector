"""Tests for device module."""

from hashlib import sha256
from unittest.mock import AsyncMock, call

import pytest

from jvcprojector import const
from jvcprojector.command import JvcCommand
from jvcprojector.device import (
    AUTH_SALT,
    HEAD_ACK,
    HEAD_OP,
    HEAD_REF,
    HEAD_RES,
    PJACK,
    PJNAK,
    PJNG,
    PJOK,
    PJREQ,
    JvcDevice,
)
from jvcprojector.error import JvcProjectorCommandError

from . import IP, PORT, TIMEOUT, cc


@pytest.mark.asyncio
async def test_send_op(conn: AsyncMock):
    """Test send operation command succeeds."""
    dev = JvcDevice(IP, PORT, TIMEOUT)
    cmd = JvcCommand(f"{const.CMD_POWER}1")
    await dev.send([cmd])
    await dev.disconnect()
    assert cmd.ack
    assert cmd.response is None
    conn.connect.assert_called_once()
    conn.write.assert_has_calls([call(PJREQ), call(cc(HEAD_OP, f"{const.CMD_POWER}1"))])


@pytest.mark.asyncio
async def test_send_ref(conn: AsyncMock):
    """Test send reference command succeeds."""
    conn.readline.side_effect = [
        cc(HEAD_ACK, const.CMD_POWER),
        cc(HEAD_RES, const.CMD_POWER + "1"),
    ]
    dev = JvcDevice(IP, PORT, TIMEOUT)
    cmd = JvcCommand(const.CMD_POWER, True)
    await dev.send([cmd])
    await dev.disconnect()
    assert cmd.ack
    assert cmd.response == const.ON
    conn.connect.assert_called_once()
    conn.write.assert_has_calls([call(PJREQ), call(cc(HEAD_REF, const.CMD_POWER))])


@pytest.mark.asyncio
async def test_send_with_password8(conn: AsyncMock):
    """Test send with 8 character password succeeds."""
    dev = JvcDevice(IP, PORT, TIMEOUT, "passwd78")
    cmd = JvcCommand(f"{const.CMD_POWER}1")
    await dev.send([cmd])
    await dev.disconnect()
    conn.write.assert_has_calls(
        [call(PJREQ + b"_passwd78\x00\x00"), call(cc(HEAD_OP, f"{const.CMD_POWER}1"))]
    )


@pytest.mark.asyncio
async def test_send_with_password10(conn: AsyncMock):
    """Test send with 10 character password succeeds."""
    dev = JvcDevice(IP, PORT, TIMEOUT, "passwd7890")
    cmd = JvcCommand(f"{const.CMD_POWER}1")
    await dev.send([cmd])
    await dev.disconnect()
    conn.write.assert_has_calls(
        [call(PJREQ + b"_passwd7890"), call(cc(HEAD_OP, f"{const.CMD_POWER}1"))]
    )


@pytest.mark.asyncio
async def test_send_with_password_sha256(conn: AsyncMock):
    """Test send with a projector requiring sha256 hashing."""
    conn.read.side_effect = [PJOK, PJNAK, PJACK]
    dev = JvcDevice(IP, PORT, TIMEOUT, "passwd78901")
    cmd = JvcCommand(f"{const.CMD_POWER}1")
    await dev.send([cmd])
    await dev.disconnect()
    auth = sha256(f"passwd78901{AUTH_SALT}".encode()).hexdigest().encode()
    conn.write.assert_has_calls(
        [call(PJREQ + b"_" + auth), call(cc(HEAD_OP, f"{const.CMD_POWER}1"))]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("conn", [{"raise_on_connect": 1}], indirect=True)
async def test_connection_refused_retry(conn: AsyncMock):
    """Test connection refused results in retry."""
    dev = JvcDevice(IP, PORT, TIMEOUT)
    cmd = JvcCommand(f"{const.CMD_POWER}1")
    await dev.send([cmd])
    await dev.disconnect()
    assert cmd.ack
    assert conn.connect.call_count == 2
    conn.write.assert_has_calls([call(PJREQ), call(cc(HEAD_OP, f"{const.CMD_POWER}1"))])


@pytest.mark.asyncio
async def test_connection_busy_retry(conn: AsyncMock):
    """Test handshake busy results in retry."""
    conn.read.side_effect = [PJNG, PJOK, PJACK]
    dev = JvcDevice(IP, PORT, TIMEOUT)
    cmd = JvcCommand(f"{const.CMD_POWER}1")
    await dev.send([cmd])
    await dev.disconnect()
    assert conn.connect.call_count == 2
    conn.write.assert_has_calls([call(PJREQ), call(cc(HEAD_OP, f"{const.CMD_POWER}1"))])


@pytest.mark.asyncio
async def test_connection_bad_handshake_error(conn: AsyncMock):
    """Test bad handshake results in error."""
    conn.read.side_effect = [b"BAD"]
    dev = JvcDevice(IP, PORT, TIMEOUT)
    cmd = JvcCommand(f"{const.CMD_POWER}1")
    with pytest.raises(JvcProjectorCommandError):
        await dev.send([cmd])
    conn.connect.assert_called_once()
    conn.disconnect.assert_called_once()
    assert not cmd.ack


@pytest.mark.asyncio
async def test_send_op_bad_ack_error(conn: AsyncMock):
    """Test send operation with bad ack results in error."""
    conn.readline.side_effect = [cc(HEAD_ACK, "ZZ")]
    dev = JvcDevice(IP, PORT, TIMEOUT)
    cmd = JvcCommand(f"{const.CMD_POWER}1")
    with pytest.raises(JvcProjectorCommandError):
        await dev.send([cmd])
    conn.connect.assert_called_once()
    conn.disconnect.assert_called_once()
    assert not cmd.ack


@pytest.mark.asyncio
async def test_send_ref_bad_ack_error(conn: AsyncMock):
    """Test send reference with bad ack results in error."""
    conn.readline.side_effect = [cc(HEAD_ACK, const.CMD_POWER), cc(HEAD_RES, "ZZ1")]
    dev = JvcDevice(IP, PORT, TIMEOUT)
    cmd = JvcCommand(const.CMD_POWER, True)
    with pytest.raises(JvcProjectorCommandError):
        await dev.send([cmd])
    conn.connect.assert_called_once()
    conn.disconnect.assert_called_once()
    assert not cmd.ack
