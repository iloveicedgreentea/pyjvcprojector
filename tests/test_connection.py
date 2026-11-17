"""Wire-level regressions against a local simulated projector."""

import asyncio
from contextlib import asynccontextmanager
from hashlib import sha256

import pytest

from jvcprojector.command import (
    AUTH_SALT,
    HEAD_ACK,
    HEAD_RES,
    PJACK,
    PJNAK,
    PJOK,
    PJREQ,
    JvcCommand,
)
from jvcprojector.device import JvcDevice

from . import cc


@asynccontextmanager
async def projector_server(respond, *, authenticate=None):
    """Serve a fragmented handshake and collect every client for cleanup."""
    tasks = set()

    async def handle(reader, writer):
        task = asyncio.current_task()
        tasks.add(task)
        try:
            writer.write(PJOK[:2])
            await writer.drain()
            await asyncio.sleep(0.001)
            writer.write(PJOK[2:])
            await writer.drain()
            if authenticate is not None:
                if not await authenticate(reader, writer):
                    return
            else:
                assert await reader.readexactly(len(PJREQ)) == PJREQ
            writer.write(PJACK[:1])
            await writer.drain()
            await asyncio.sleep(0.001)
            writer.write(PJACK[1:])
            await writer.drain()
            await respond(reader, writer)
        finally:
            writer.close()
            await writer.wait_closed()
            tasks.remove(task)

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    try:
        yield server.sockets[0].getsockname()[1]
    finally:
        server.close()
        await server.wait_closed()
        for task in tuple(tasks):
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


@pytest.mark.asyncio
async def test_fragmented_tcp_handshake():
    """TCP packet boundaries must not be mistaken for JVC frame boundaries."""

    async def respond(reader, writer):
        assert await reader.readline() == b"!\x89\x01RC7301\n"
        writer.write(cc(HEAD_ACK, "RC"))
        await writer.drain()
        await reader.read()

    async with projector_server(respond) as port:
        device = JvcDevice("127.0.0.1", port, 1)
        cmd = JvcCommand("RC7301")
        try:
            await device.send([cmd])
            assert cmd.ack
        finally:
            await device.disconnect()


@pytest.mark.asyncio
async def test_modern_auth_reconnects_after_legacy_password_rejection():
    """A SHA256-only model can close PJNAK without breaking auth fallback."""
    attempts = []
    expected = sha256(f"12345678{AUTH_SALT}".encode()).hexdigest().encode()

    async def authenticate(reader, writer):
        data = await reader.readexactly(len(PJREQ) + 1 + (10 if not attempts else 64))
        attempts.append(data)
        if len(attempts) == 1:
            writer.write(PJNAK)
            await writer.drain()
            return False
        assert data == PJREQ + b"_" + expected
        return True

    async def respond(reader, writer):
        assert await reader.readline() == b"!\x89\x01RC7301\n"
        writer.write(cc(HEAD_ACK, "RC"))
        await writer.drain()
        await reader.read()

    async with projector_server(respond, authenticate=authenticate) as port:
        device = JvcDevice("127.0.0.1", port, 1, "12345678")
        try:
            command = JvcCommand("RC7301")
            await device.send([command])
            assert command.ack
            assert len(attempts) == 2
        finally:
            await device.disconnect()


@pytest.mark.asyncio
async def test_optional_timeout_opens_fresh_tcp_stream(monkeypatch):
    """An unanswered optional query cannot contaminate the following reply."""
    monkeypatch.setattr("jvcprojector.device.REF_TIMEOUT", 0.01)
    commands = []

    async def respond(reader, writer):
        data = await reader.readline()
        commands.append(data)
        if data == b"?\x89\x01PMLL\n":
            # No ACK: the client must close instead of sending PW here.
            assert await reader.read() == b""
        else:
            assert data == b"?\x89\x01PW\n"
            writer.write(cc(HEAD_ACK, "PW") + cc(HEAD_RES, "PW1"))
            await writer.drain()
            await reader.read()

    async with projector_server(respond) as port:
        device = JvcDevice("127.0.0.1", port, 1)
        power = JvcCommand("PW", True)
        try:
            await device.send([JvcCommand("PMLL", True), power])
            assert power.response == "on"
            assert commands == [b"?\x89\x01PMLL\n", b"?\x89\x01PW\n"]
        finally:
            await device.disconnect()
