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

        self._last: float = 0.0

    async def send(self, cmds: list[JvcCommand]) -> None:
        """Send commands to device."""
        try:
            await self._connect()
            for cmd in cmds:
                await self._send(cmd)
                # If power is standby, skip remaining checks that will timeout
                if cmd.is_ref and cmd.is_power and cmd.response != const.ON:
                    break
        finally:
            await self._disconnect()

    async def _connect(self) -> None:
        """Connect to device."""
        elapsed = time() - self._last
        if elapsed < 0.75:
            await asyncio.sleep(0.75 - elapsed)

        retries = 0
        while retries < 16:
            try:
                _LOGGER.debug("Connecting to %s", self._conn.ip)
                await self._conn.connect()
            except ConnectionRefusedError:
                retries += 1
                if retries == 12:
                    _LOGGER.warning("Retrying refused connection")
                else:
                    _LOGGER.debug("Retrying refused connection")
                await asyncio.sleep(0.1 * retries)
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

    async def _disconnect(self) -> None:
        """Disconnect from device."""
        await self._conn.disconnect()
        _LOGGER.debug("Disconnected")
