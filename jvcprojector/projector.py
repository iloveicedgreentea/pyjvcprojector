"""Module for interacting with a JVC Projector."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Optional

from . import command, const
from .command import JvcCommand, TEST
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
        password: Optional[str] = None,
    ) -> None:
        """Initialize class."""
        self._host = host
        self._port = port
        self._timeout = timeout
        self._password = password

        self._device: Optional[JvcDevice] = None
        self._ip: str = ""
        self._model: str = ""
        self._mac: str = ""
        self._version: str = ""

        self._lock = asyncio.Lock()

    @property
    def ip(self) -> str:
        """Returns ip."""
        if not self._ip:
            raise JvcProjectorError("ip not initialized")
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
    def model(self) -> str:
        """Returns model name."""
        if not self._mac:
            raise JvcProjectorError("model not initialized")
        return self._model

    @property
    def mac(self) -> str:
        """Returns mac address."""
        if not self._mac:
            raise JvcProjectorError("mac address not initialized")
        return self._mac

    @property
    def version(self) -> str:
        """Get device software version."""
        if not self._version:
            raise JvcProjectorError("version address not initialized")
        return self._version

    async def connect(self, get_info: bool = False) -> None:
        """Connect to device."""
        if self._device:
            return

        if not self._ip:
            self._ip = await resolve(self._host)

        self._device = JvcDevice(self._ip, self._port, self._timeout, self._password)
        await self._device.connect()

        if not await self.test():
            raise JvcProjectorConnectError("Failed to verify connection")

        if get_info:
            await self.get_info()

    async def disconnect(self) -> None:
        """Disconnect from device."""
        await self._device.disconnect()
        self._device = None

    async def get_info(self) -> dict[str, str]:
        """Get device info."""
        model = JvcCommand(command.MODEL, True)
        mac = JvcCommand(command.MAC, True)
        await self._send([model, mac])

        if model.response is None:
            model.response = "(unknown)"

        if mac.response is None:
            _LOGGER.warning("Mac address unavailable, using hash of model")
            mac.response = hashlib.md5(model.response.encode()).digest().hex()[0:14]

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

    async def get_version(self) -> Optional[str]:
        """Get device software version."""
        return await self.ref(command.VERSION)

    async def get_power(self) -> Optional[str]:
        """Get power state."""
        return await self.ref(command.POWER)

    async def get_input(self) -> Optional[str]:
        """Get current input."""
        return await self.ref(command.INPUT)

    async def get_signal(self) -> Optional[str]:
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

    async def ref(self, code: str) -> Optional[str]:
        """Send reference code."""
        return (await self._send([JvcCommand(code, True)]))[0]

    async def _send(self, cmds: list[JvcCommand]) -> list[Optional[str]]:
        """Send command to device."""
        if self._device is None:
            raise JvcProjectorError("Must connect before sending commands")

        if not self._device.is_connected():
            await self._device.connect()

        async with self._lock:
            try:
                for cmd in cmds:
                    await self._device.send(cmd)
                    if not cmd.ack:
                        # An un-acked command can be normal, but can also but can also mean
                        # the device remotely disconnected. Send a test command to confirm.
                        cmd = JvcCommand(TEST)
                        await self._device.send(cmd)
                        if not cmd.ack:
                            _LOGGER.debug("Remote end disconnected")
                            await self._device.disconnect()
                            await asyncio.sleep(20)
                            break

                    # If power is standby, skip remaining checks that will timeout anyway.
                    if cmd.is_ref and cmd.is_power and cmd.response != const.ON:
                        break
            except JvcProjectorError:
                await self._device.disconnect()
                raise

        return [cmd.response for cmd in cmds]
