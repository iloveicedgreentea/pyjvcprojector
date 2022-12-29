"""Tests for device module."""

from unittest.mock import AsyncMock, call

import pytest

from jvcprojector import command, const
from jvcprojector.command import JvcCommand
from jvcprojector.device import (
    HEAD_ACK,
    HEAD_OP,
    HEAD_REF,
    HEAD_RES,
    PJACK,
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
    cmd = JvcCommand(f"{command.POWER}1")
    await dev.send([cmd])
    assert cmd.ack
    assert cmd.response is None
    conn.connect.assert_called_once()
    conn.write.assert_has_calls([call(PJREQ), call(cc(HEAD_OP, f"{command.POWER}1"))])


@pytest.mark.asyncio
async def test_send_ref(conn: AsyncMock):
    """Test send reference command succeeds."""
    conn.readline.side_effect = [
        cc(HEAD_ACK, command.POWER),
        cc(HEAD_RES, command.POWER + "1"),
    ]
    dev = JvcDevice(IP, PORT, TIMEOUT)
    cmd = JvcCommand(command.POWER, True)
    await dev.send([cmd])
    assert cmd.ack
    assert cmd.response == const.ON
    conn.connect.assert_called_once()
    conn.write.assert_has_calls([call(PJREQ), call(cc(HEAD_REF, command.POWER))])


@pytest.mark.asyncio
async def test_send_with_password8(conn: AsyncMock):
    """Test send with 8 character password succeeds."""
    dev = JvcDevice(IP, PORT, TIMEOUT, "passwd78")
    cmd = JvcCommand(f"{command.POWER}1")
    await dev.send([cmd])
    conn.write.assert_has_calls(
        [call(PJREQ + b"_passwd78\x00\x00"), call(cc(HEAD_OP, f"{command.POWER}1"))]
    )


@pytest.mark.asyncio
async def test_send_with_password10(conn: AsyncMock):
    """Test send with 10 character password succeeds."""
    dev = JvcDevice(IP, PORT, TIMEOUT, "passwd7890")
    cmd = JvcCommand(f"{command.POWER}1")
    await dev.send([cmd])
    conn.write.assert_has_calls(
        [call(PJREQ + b"_passwd7890"), call(cc(HEAD_OP, f"{command.POWER}1"))]
    )


@pytest.mark.asyncio
async def test_connection_refused_retry(conn: AsyncMock):
    """Test connection refused results in retry."""
    conn.connect.side_effect = [ConnectionRefusedError, None]
    dev = JvcDevice(IP, PORT, TIMEOUT)
    cmd = JvcCommand(f"{command.POWER}1")
    await dev.send([cmd])
    assert cmd.ack
    assert conn.connect.call_count == 2
    conn.write.assert_has_calls([call(PJREQ), call(cc(HEAD_OP, f"{command.POWER}1"))])


@pytest.mark.asyncio
async def test_connection_busy_retry(conn: AsyncMock):
    """Test handshake busy results in retry."""
    conn.read.side_effect = [PJNG, PJOK, PJACK]
    dev = JvcDevice(IP, PORT, TIMEOUT)
    cmd = JvcCommand(f"{command.POWER}1")
    await dev.send([cmd])
    assert conn.connect.call_count == 2
    conn.write.assert_has_calls([call(PJREQ), call(cc(HEAD_OP, f"{command.POWER}1"))])


@pytest.mark.asyncio
async def test_connection_bad_handshake_error(conn: AsyncMock):
    """Test bad handshake results in error."""
    conn.read.side_effect = [b"BAD"]
    dev = JvcDevice(IP, PORT, TIMEOUT)
    cmd = JvcCommand(f"{command.POWER}1")
    with pytest.raises(JvcProjectorCommandError):
        await dev.send([cmd])
    conn.connect.assert_called_once()
    assert not cmd.ack


@pytest.mark.asyncio
async def test_send_op_bad_ack_error(conn: AsyncMock):
    """Test send operation with bad ack results in error."""
    conn.readline.side_effect = [cc(HEAD_ACK, "ZZ")]
    dev = JvcDevice(IP, PORT, TIMEOUT)
    cmd = JvcCommand(f"{command.POWER}1")
    with pytest.raises(JvcProjectorCommandError):
        await dev.send([cmd])
    conn.connect.assert_called_once()
    assert not cmd.ack


@pytest.mark.asyncio
async def test_send_ref_bad_ack_error(conn: AsyncMock):
    """Test send reference with bad ack results in error."""
    conn.readline.side_effect = [cc(HEAD_ACK, command.POWER), cc(HEAD_RES, "ZZ1")]
    dev = JvcDevice(IP, PORT, TIMEOUT)
    cmd = JvcCommand(command.POWER, True)
    with pytest.raises(JvcProjectorCommandError):
        await dev.send([cmd])
    conn.connect.assert_called_once()
    assert not cmd.ack
