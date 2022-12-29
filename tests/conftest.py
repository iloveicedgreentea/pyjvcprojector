"""pytest fixtures"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from jvcprojector import command, const
from jvcprojector.command import JvcCommand
from jvcprojector.device import HEAD_ACK, PJACK, PJOK

from . import IP, MAC, MODEL, PORT, cc


@pytest.fixture(name="conn")
def fixture_mock_connection():
    """Return a mocked connection."""
    with patch("jvcprojector.device.JvcConnection", autospec=True) as mock:
        conn = mock.return_value
        conn.ip = IP
        conn.port = PORT
        conn.is_connected.return_value = False
        conn.read.side_effect = [PJOK, PJACK]
        conn.readline.side_effect = [cc(HEAD_ACK, command.POWER)]
        conn.write = AsyncMock(return_value=None)
        yield conn


@pytest.fixture(name="dev")
def fixture_mock_device(request):
    """Return a mocked device."""
    with patch("jvcprojector.projector.JvcDevice", autospec=True) as mock:
        fixture = {
            command.TEST: None,
            command.MAC: MAC,
            command.MODEL: MODEL,
            command.POWER: const.ON,
            command.INPUT: const.INPUT_HDMI1,
            command.SOURCE: const.SIGNAL,
        }

        if hasattr(request, "param"):
            fixture.update(request.param)

        async def send(cmds: list[JvcCommand]):
            for cmd in cmds:
                if cmd.code in fixture:
                    if fixture[cmd.code]:
                        cmd.response = fixture[cmd.code]
                    cmd.ack = True

        dev = mock.return_value
        dev.send.side_effect = send

        yield dev
