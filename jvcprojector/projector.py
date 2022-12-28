"""Module for interacting with a JVC Projector."""

from __future__ import annotations

import asyncio
import hashlib
import logging

from . import command, const
from .command import JvcCommand
from .connection import resolve
from .device import JvcDevice
from .error import JvcProjectorConnectError, JvcProjectorError

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 20554
DEFAULT_TIMEOUT = 5.0


class JvcProjector:
    """Class for interacting with a JVC Projector."""

    def __init__(
        self,
        host: str,
        *,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT,
        password: str | None = None,
    ) -> None:
        """Initialize class."""
        self._host = host
        self._port = port
        self._timeout = timeout
        self._password = password

        self._device: JvcDevice | None = None
        self._ip: str | None = None
        self._model: str | None = None
        self._mac: str | None = None
        self._version: str | None = None

        self._lock = asyncio.Lock()
        self._connected = False

    @property
    def ip(self) -> str | None:
        """Returns ip."""
        return self._ip

    @property
    def host(self) -> str:
        """Returns host."""
        return self._host

    @property
    def port(self) -> int:
        """Returns port."""
        return self._port

    @property
    def model(self) -> str | None:
        """Returns model name."""
        return self._model

    @property
    def mac(self) -> str | None:
        """Returns mac address."""
        return self._mac

    @property
    def version(self) -> str | None:
        """Get device software version."""
        return self._version

    async def connect(self, get_info: bool = False) -> None:
        """Connect to devices."""
        if self._connected:
            return

        if self._ip is None:
            self._ip = await resolve(self._host)

        self._device = JvcDevice(self._ip, self._port, self._timeout, self._password)

        if not await self.test():
            raise JvcProjectorConnectError("Failed to verify connection")

        if get_info:
            await self.get_info()

        self._connected = True

    async def disconnect(self) -> None:
        """Disconnect from device."""
        self._device = None
        self._connected = False

    async def get_info(self) -> dict[str, str]:
        """Get device info."""
        model = JvcCommand(command.MODEL, True)
        mac = JvcCommand(command.MAC, True)
        await self._send([model, mac])

        if model.response is None:
            model.response = "(unknown)"

        if mac.response is None:
            _LOGGER.warning("Mac address unavailable, using hash of model")
            mac.response = hashlib.md5(model.response.encode()).digest().hex()[0:12]

        self._model = model.response
        self._mac = mac.response

        return {"model": self._model, "mac": self._mac}

    async def get_state(self) -> dict[str, str]:
        """Get device state."""
        pwr = JvcCommand(command.POWER, True)
        inp = JvcCommand(command.INPUT, True)
        src = JvcCommand(command.SOURCE, True)
        res = await self._send([pwr, inp, src])
        return {
            "power": res[0] or "",
            "input": res[1] or const.NOSIGNAL,
            "source": res[2] or const.NOSIGNAL,
        }

    async def get_version(self) -> str | None:
        """Get device software version."""
        return await self.ref(command.VERSION)

    async def get_power(self) -> str | None:
        """Get power state."""
        return await self.ref(command.POWER)

    async def get_input(self) -> str | None:
        """Get current input."""
        return await self.ref(command.INPUT)

    async def get_signal(self) -> str | None:
        """Get if has signal."""
        return await self.ref(command.SOURCE)

    async def test(self) -> bool:
        """Run test command."""
        cmd = JvcCommand(f"{command.TEST}")
        await self._send([cmd])
        return cmd.ack

    async def power_on(self) -> None:
        """Run power on command."""
        await self.op(f"{command.POWER}1")

    async def power_off(self) -> None:
        """Run power off command."""
        await self.op(f"{command.POWER}0")

    async def remote(self, code: str) -> None:
        """Run remote code command."""
        await self.op(f"{command.REMOTE}{code}")

    async def op(self, code: str) -> None:
        """Send operation code."""
        await self._send([JvcCommand(code, False)])

    async def ref(self, code: str) -> str | None:
        """Send reference code."""
        return (await self._send([JvcCommand(code, True)]))[0]

    async def _send(self, cmds: list[JvcCommand]) -> list[str | None]:
        """Send command to device."""
        if self._device is None:
            raise JvcProjectorError("Must call connect before sending commands")

        async with self._lock:
            await self._device.send(cmds)

        return [cmd.response for cmd in cmds]
