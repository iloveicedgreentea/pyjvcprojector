"""Opt-in, read-only checks against a real projector."""

import logging
import os

import pytest

from jvcprojector.projector import JvcProjector
from jvcprojector import const

_LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION") != "true", reason="Set RUN_INTEGRATION to true"
)
async def test_connect():
    """Read real device information without changing power or picture settings."""
    ip = os.getenv("JVC_IP")
    if not ip:
        pytest.fail("Set JVC_IP to the projector's hostname or IP address")

    projector = JvcProjector(ip, password=os.getenv("JVC_PASSWORD"))
    try:
        await projector.connect(get_info=True)
        state = await projector.get_state()
        assert state[const.KEY_POWER] in const.VAL_POWER
        _LOGGER.info(
            "Projector model: %s; power: %s", projector.model, state[const.KEY_POWER]
        )
    finally:
        await projector.disconnect()
