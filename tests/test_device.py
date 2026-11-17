"""Tests for device module."""

import asyncio
from hashlib import sha256
from unittest.mock import AsyncMock, call, patch

import pytest

from jvcprojector import const
from jvcprojector.command import JvcCommand
from jvcprojector.device import (
    AUTH_SALT,
    COMMAND_INTERVAL,
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
from jvcprojector.error import JvcProjectorCommandError, JvcProjectorConnectError

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
    conn.read.side_effect = [PJOK, PJNAK, PJOK, PJACK]
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


@pytest.mark.asyncio
async def test_optional_timeout_reconnects_before_next_command(conn: AsyncMock):
    """Discard a timed-out stream before continuing a refresh."""
    conn.read.side_effect = [PJOK, PJACK, PJOK, PJACK]
    conn.readline.side_effect = [
        asyncio.TimeoutError(),
        cc(HEAD_ACK, const.CMD_POWER),
        cc(HEAD_RES, const.CMD_POWER + "1"),
    ]
    dev = JvcDevice(IP, PORT, TIMEOUT)
    optional = JvcCommand(const.CMD_PICTURE_MODE_LOW_LATENCY, True)
    power = JvcCommand(const.CMD_POWER, True)
    await dev.send([optional, power])
    assert not optional.ack
    assert power.response == const.ON
    assert conn.connect.call_count == 2
    assert conn.disconnect.call_count == 1
    assert not dev.is_command_supported(optional.code)
    await dev.disconnect()


@pytest.mark.asyncio
@pytest.mark.parametrize("is_ref", [False, True])
async def test_power_timeout_is_reported(conn: AsyncMock, is_ref: bool):
    """Power reads and operations must never be silently ignored."""
    conn.readline.side_effect = asyncio.TimeoutError()
    dev = JvcDevice(IP, PORT, TIMEOUT)
    cmd = JvcCommand(const.CMD_POWER if is_ref else const.CMD_POWER + "1", is_ref)
    with pytest.raises(JvcProjectorConnectError, match="Response timeout"):
        await dev.send([cmd])
    assert not cmd.ack
    assert dev.is_command_supported(cmd.code)
    assert not conn.is_connected()


@pytest.mark.asyncio
async def test_optional_timeout_cache_expires(conn: AsyncMock):
    """Retry optional references after a bounded backoff or explicit reset."""
    conn.readline.side_effect = asyncio.TimeoutError()
    dev = JvcDevice(IP, PORT, TIMEOUT)
    code = const.CMD_PICTURE_MODE_LOW_LATENCY
    with patch("jvcprojector.device.monotonic", return_value=100):
        await dev.send([JvcCommand(code, True)])
        assert dev.get_unsupported_commands() == {code}
        conn.connect.reset_mock()
        await dev.send([JvcCommand(code, True)])
        conn.connect.assert_not_called()
    with patch("jvcprojector.device.monotonic", return_value=401):
        assert dev.get_unsupported_commands() == set()
    dev.clear_unsupported_commands()
    await dev.disconnect()


@pytest.mark.asyncio
async def test_optional_timeout_does_not_suppress_operation(conn: AsyncMock):
    """An unresponsive read must never disable a setter for the same code."""
    conn.readline.side_effect = asyncio.TimeoutError()
    dev = JvcDevice(IP, PORT, TIMEOUT)
    code = const.CMD_PICTURE_MODE_LOW_LATENCY
    await dev.send([JvcCommand(code, True)])
    conn.read.side_effect = [PJOK, PJACK]
    conn.readline.side_effect = [cc(HEAD_ACK, code[:2])]
    cmd = JvcCommand(code + "1")
    await dev.send([cmd])
    assert cmd.ack
    await dev.disconnect()


@pytest.mark.asyncio
async def test_cancel_drops_stream(conn: AsyncMock):
    """Cancellation during a command closes the stream before another request."""
    started = asyncio.Event()

    async def pending_read(**kwargs):
        started.set()
        await asyncio.Event().wait()

    conn.readline.side_effect = pending_read
    dev = JvcDevice(IP, PORT, TIMEOUT)
    task = asyncio.create_task(dev.send([JvcCommand("RC7301")]))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not conn.is_connected()


@pytest.mark.asyncio
async def test_sha256_short_password_uses_unpadded_text(conn: AsyncMock):
    """Hash the password itself instead of legacy zero-padding bytes."""
    conn.read.side_effect = [PJOK, PJNAK, PJOK, PJACK]
    dev = JvcDevice(IP, PORT, TIMEOUT, "short")
    await dev.send([JvcCommand(const.CMD_POWER + "1")])
    auth = sha256(f"short{AUTH_SALT}".encode()).hexdigest().encode()
    assert call(PJREQ + b"_" + auth) in conn.write.call_args_list
    await dev.disconnect()


@pytest.mark.asyncio
async def test_ref_missing_terminator_rejected(conn: AsyncMock):
    """EOF cannot turn an incomplete response into a valid state."""
    conn.readline.side_effect = [cc(HEAD_ACK, "PW"), cc(HEAD_RES, "PW1")[:-1]]
    dev = JvcDevice(IP, PORT, TIMEOUT)
    with pytest.raises(JvcProjectorCommandError, match="Ref ack invalid"):
        await dev.send([JvcCommand("PW", True)])
    assert not conn.is_connected()


@pytest.mark.asyncio
async def test_single_command_returns_without_post_ack_delay(conn: AsyncMock):
    """A caller receives an acknowledged key without an unnecessary final wait."""
    dev = JvcDevice(IP, PORT, TIMEOUT)
    cmd = JvcCommand(const.CMD_POWER + "1")
    with patch("jvcprojector.device.asyncio.sleep", new_callable=AsyncMock) as sleep:
        await dev.send([cmd])
        assert cmd.ack
        sleep.assert_not_awaited()
        await dev.disconnect()


@pytest.mark.asyncio
@pytest.mark.parametrize("separate_calls", [False, True])
async def test_command_recovery_spacing_across_batches_and_calls(
    conn: AsyncMock, separate_calls: bool
):
    """Preserve the full recovery interval after responses on a reused stream."""
    now = [100.0]
    writes = []

    async def sleep(delay):
        now[0] += delay

    def write(data):
        if data.startswith(HEAD_OP):
            writes.append(now[0])

    def ack(**kwargs):
        now[0] += 0.05
        return cc(HEAD_ACK, const.CMD_POWER)

    conn.write.side_effect = write
    conn.readline.side_effect = ack
    dev = JvcDevice(IP, PORT, TIMEOUT)
    commands = [JvcCommand(const.CMD_POWER + "1") for _ in range(2)]
    with (
        patch("jvcprojector.device.monotonic", side_effect=lambda: now[0]),
        patch("jvcprojector.device.asyncio.sleep", side_effect=sleep) as paced_sleep,
    ):
        if separate_calls:
            await dev.send(commands[:1])
            now[0] += 0.05
            await dev.send(commands[1:])
        else:
            await dev.send(commands)
        assert writes == pytest.approx([100.0, 100.05 + COMMAND_INTERVAL])
        assert now[0] == pytest.approx(100.10 + COMMAND_INTERVAL)
        paced_sleep.assert_awaited_once()
        await dev.disconnect()


@pytest.mark.asyncio
async def test_elapsed_idle_time_satisfies_command_recovery(conn: AsyncMock):
    """Ordinary slow taps do not acquire a second artificial recovery delay."""
    now = [100.0]
    conn.readline.side_effect = None
    conn.readline.return_value = cc(HEAD_ACK, const.CMD_POWER)
    dev = JvcDevice(IP, PORT, TIMEOUT)
    with (
        patch("jvcprojector.device.monotonic", side_effect=lambda: now[0]),
        patch("jvcprojector.device.asyncio.sleep", new_callable=AsyncMock) as sleep,
    ):
        await dev.send([JvcCommand(const.CMD_POWER + "1")])
        now[0] += COMMAND_INTERVAL + 0.1
        await dev.send([JvcCommand(const.CMD_POWER + "1")])
        sleep.assert_not_awaited()
        await dev.disconnect()


@pytest.mark.asyncio
async def test_cancel_during_recovery_does_not_send_next_command(conn: AsyncMock):
    """Cancelling the pacing wait closes the stream without writing another key."""
    dev = JvcDevice(IP, PORT, TIMEOUT)
    with patch("jvcprojector.device.monotonic", return_value=100):
        await dev.send([JvcCommand(const.CMD_POWER + "1")])
        conn.write.reset_mock()
        with (
            patch(
                "jvcprojector.device.asyncio.sleep", side_effect=asyncio.CancelledError
            ),
            pytest.raises(asyncio.CancelledError),
        ):
            await dev.send([JvcCommand(const.CMD_POWER + "1")])
        conn.write.assert_not_awaited()
        assert not conn.is_connected()
