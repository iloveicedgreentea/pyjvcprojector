"""Module for representing a JVC Projector device."""

from __future__ import annotations

import asyncio
import logging
import struct
from time import time
from typing import TYPE_CHECKING

from . import const
from .command import (
    END,
    HEAD_ACK,
    HEAD_LEN,
    HEAD_OP,
    HEAD_REF,
    HEAD_RES,
    PJACK,
    PJNAK,
    PJNG,
    PJOK,
    PJREQ,
)
from .connection import JvcConnection
from .error import (
    JvcProjectorAuthError,
    JvcProjectorCommandError,
    JvcProjectorConnectError,
)

if TYPE_CHECKING:
    from .command import JvcCommand

_LOGGER = logging.getLogger(__name__)


class JvcDevice:
    """Class for representing a JVC Projector device."""

    def __init__(
        self, ip: str, port: int, timeout: float, password: str | None = None
    ) -> None:
        """Initialize class."""
        self._conn = JvcConnection(ip, port, timeout)

        self._auth = b""
        if password:
            self._auth = b"_" + struct.pack("10s", password.encode())

        self._lock = asyncio.Lock()
        self._keepalive: asyncio.Task | None = None
        self._last: float = 0.0

    async def send(self, cmds: list[JvcCommand]) -> None:
        """Send commands to device."""
        async with self._lock:
            # Treat status refreshes with special handling
            is_refresh = len(cmds) > 1 and cmds[0].is_ref and cmds[0].is_power

            # Connection keepalive window for fast command repeats
            keepalive = True

            # Connection keepalive window for fast command repeats
            if self._keepalive:
                self._keepalive.cancel()
                self._keepalive = None
            elif is_refresh:
                # Don't extend window below if this was a refresh
                keepalive = False

            try:
                if not self._conn.is_connected():
                    await self._connect()

                for cmd in cmds:
                    await self._send(cmd)
                    # If device is not on skip remaining commands
                    if is_refresh and cmd.response != const.ON:
                        break
            except Exception:
                keepalive = False
                raise
            finally:
                # Delay disconnect to keep connection alive
                if keepalive:
                    self._keepalive = asyncio.create_task(self._disconnect(5))
                else:
                    await self._disconnect()

    async def _connect(self) -> None:
        """Connect to device."""
        assert not self._conn.is_connected()

        elapsed = time() - self._last
        if elapsed < 0.75:
            await asyncio.sleep(0.75 - elapsed)

        retries = 0
        while retries < 10:
            try:
                _LOGGER.debug("Connecting to %s", self._conn.ip)
                await self._conn.connect()
            except ConnectionRefusedError:
                retries += 1
                if retries == 5:
                    _LOGGER.warning("Retrying refused connection")
                else:
                    _LOGGER.debug("Retrying refused connection")
                await asyncio.sleep(0.2 * retries)
                continue
            except (asyncio.TimeoutError, ConnectionError) as err:
                raise JvcProjectorConnectError from err

            try:
                data = await self._conn.read(len(PJOK))
            except asyncio.TimeoutError as err:
                raise JvcProjectorConnectError("Handshake init timeout") from err

            _LOGGER.debug("Handshake received %s", data)

            if data == PJNG:
                _LOGGER.warning("Handshake retrying on busy")
                retries += 1
                await asyncio.sleep(0.25 * retries)
                continue

            if data != PJOK:
                raise JvcProjectorCommandError("Handshake init invalid")

            break
        else:
            raise JvcProjectorConnectError("Retries exceeded")

        _LOGGER.debug("Handshake sending '%s'", PJREQ.decode())
        await self._conn.write(PJREQ + self._auth)

        try:
            data = await self._conn.read(len(PJACK))
        except asyncio.TimeoutError as err:
            raise JvcProjectorConnectError("Handshake ack timeout") from err

        _LOGGER.debug("Handshake received %s", data)

        if data == PJNAK:
            raise JvcProjectorAuthError()

        if data != PJACK:
            raise JvcProjectorCommandError("Handshake ack invalid")

        self._last = time()

    async def _send(self, cmd: JvcCommand) -> None:
        """Send command to device."""
        assert self._conn.is_connected()
        assert len(cmd.code) >= 2

        code = cmd.code.encode()
        data = (HEAD_REF if cmd.is_ref else HEAD_OP) + code + END

        _LOGGER.debug(
            "Sending %s '%s (%s)'", "ref" if cmd.is_ref else "op", cmd.code, data
        )
        await self._conn.write(data)

        try:
            data = await self._conn.readline()
        except asyncio.TimeoutError:
            _LOGGER.warning("Response timeout for '%s'", cmd.code)
            return

        _LOGGER.debug("Received ack %s", data)

        if not data.startswith(HEAD_ACK + code[0:2]):
            raise JvcProjectorCommandError(
                f"Response ack invalid '{data!r}' for '{cmd.code}'"
            )

        if cmd.is_ref:
            try:
                data = await self._conn.readline()
            except asyncio.TimeoutError:
                _LOGGER.warning("Ref response timeout for '%s'", cmd.code)
                return

            _LOGGER.debug("Received ref %s (%s)", data[HEAD_LEN + 2 : -1], data)

            if not data.startswith(HEAD_RES + code[0:2]):
                raise JvcProjectorCommandError(
                    f"Ref ack invalid '{data!r}' for '{cmd.code}'"
                )

            try:
                cmd.response = data[HEAD_LEN + 2 : -1].decode()
            except UnicodeDecodeError:
                cmd.response = data.hex()
                _LOGGER.warning("Failed to decode response '%s'", data)

        cmd.ack = True

    async def disconnect(self) -> None:
        """Disconnect from device."""
        if self._keepalive:
            self._keepalive.cancel()
        await self._disconnect()

    async def _disconnect(self, delay: int = 0) -> None:
        """Disconnect from device."""
        if delay:
            await asyncio.sleep(delay)
        self._keepalive = None
        await self._conn.disconnect()
        _LOGGER.debug("Disconnected")
