"""Module for interacting with a JVC Projector."""

from __future__ import annotations

from . import command
from .command import JvcCommand
from .connection import resolve
from .device import JvcDevice
from .error import JvcProjectorConnectError, JvcProjectorError
from . import const

DEFAULT_PORT = 20554
DEFAULT_TIMEOUT = 15.0


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
        self._ip: str = ""
        self._model: str = ""
        self._mac: str = ""
        self._version: str = ""
        self._dict: dict[str, str] = {}

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

        if not await self.test():
            raise JvcProjectorConnectError("Failed to verify connection")

        if get_info:
            await self.get_info()

    async def disconnect(self) -> None:
        """Disconnect from device."""
        if self._device:
            await self._device.disconnect()
            self._device = None

    async def get_info(self) -> dict[str, str]:
        """Get device info."""
        if not self._device:
            raise JvcProjectorError("Must call connect before getting info")

        model = JvcCommand(command.MODEL, True)
        mac = JvcCommand(command.MAC, True)
        version = JvcCommand(command.VERSION, True)
        await self._send([model, mac, version])

        if mac.response is None:
            mac.response = "(unknown)"

        if model.response is None:
            model.response = "(unknown)"

        # store to reference in state
        self._model = model.response
        self._mac = mac.response
        self._version = version.response

        return {const.KEY_MODEL: self._model, const.KEY_MAC: self._mac}

    async def get_state(self) -> dict[str, str | None]:
        """Get device state."""
        if not self._device:
            raise JvcProjectorError("Must call connect before getting state")

        # Add static values
        # TODO: make these keys const so HA can reference them
        self._dict[const.KEY_MODEL] = self.process_model_code(self._model)
        self._dict[const.KEY_VERSION] = self.process_version(self._version)
        self._dict[const.KEY_MAC] = self.process_mac(self._mac)

        async def send_and_update(commands: dict[str, str]) -> None:
            """Send commands and update the dictionary."""
            cmd_vals = [JvcCommand(cmd, True) for cmd in commands.values()]
            res = await self._send(cmd_vals)
            # discard the command values and zip the keys with the responses
            for (key, _), value in zip(commands.items(), res):
                self._dict[key] = value

        # Always get power state
        await send_and_update({const.KEY_POWER: command.POWER})

        # If power is on, get additional states
        if self._dict.get(const.KEY_POWER) == const.ON:
            await send_and_update(
                {
                    const.KEY_INPUT: command.INPUT,
                    const.KEY_SOURCE: command.SOURCE,
                    const.KEY_PICTURE_MODE: command.PICTURE_MODE,
                    const.KEY_LOW_LATENCY: command.LOW_LATENCY,
                    const.KEY_LASER_POWER: command.LASER_POWER,
                    const.KEY_ANAMORPHIC: command.ANAMORPHIC,
                    const.KEY_INSTALLATION_MODE: command.INSTALLATION_MODE,
                }
            )

            # Check if there's a signal before getting signal-dependent states
            if self._dict.get(const.KEY_SOURCE) == const.SIGNAL:
                await send_and_update(
                    {
                        const.KEY_HDR: command.HDR,
                        const.KEY_HDMI_INPUT_LEVEL: command.HDMI_INPUT_LEVEL,
                        const.KEY_HDMI_COLOR_SPACE: command.HDMI_COLOR_SPACE,
                        const.KEY_COLOR_PROFILE: command.COLOR_PROFILE,
                        const.KEY_GRAPHICS_MODE: command.GRAPHICS_MODE,
                        const.KEY_COLOR_SPACE: command.COLOR_SPACE,
                    }
                )

            # NX9 and NZ model specific commands
            if (
                "NZ" in self._dict[const.KEY_MODEL]
                or "NX9" in self._dict[const.KEY_MODEL]
            ):
                await send_and_update(
                    {
                        const.KEY_ESHIFT: command.ESHIFT,
                        const.KEY_CLEAR_MOTION_DRIVE: command.CLEAR_MOTION_DRIVE,
                        const.KEY_MOTION_ENHANCE: command.MOTION_ENHANCE,
                        const.KEY_LASER_VALUE: command.LASER_VALUE,
                        const.KEY_LASER_TIME: command.LASER_TIME,
                        const.KEY_LASER_DIMMING: command.LASER_DIMMING,
                    }
                )

            # HDR-specific commands
            if self._dict.get("hdr") != const.HDR_CONTENT_SDR:
                await send_and_update(
                    {
                        const.KEY_HDR_PROCESSING: command.HDR_PROCESSING,
                        const.KEY_HDR_CONTENT_TYPE: command.HDR_CONTENT_TYPE,
                    }
                )

        return self._dict

    def process_mac(self, mac: str) -> str:
        """Process mac address."""
        # skip every 2 characters and join with :
        return ":".join(mac[i : i + 2] for i in range(0, len(mac), 2))

    def process_model_code(self, model: str) -> str:
        """Process model code."""
        return const.MODEL_MAP.get(model[-4:], "Unsupported")

    def process_version(self, version: str) -> str:
        """Process version string."""
        version = version.removesuffix("PJ")
        version = version.zfill(4)

        # Extract major, minor, and patch versions
        major = str(
            int(version[0:2])
        )  # Remove leading zero and convert to int then back to str
        minor = str(int(version[2]))
        patch = str(int(version[3]))

        return f"{major}.{minor}.{patch}"

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

        await self._device.send(cmds)

        return [cmd.response for cmd in cmds]
