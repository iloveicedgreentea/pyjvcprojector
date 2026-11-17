"""System resolver regressions without external DNS or runtime packages."""

import asyncio
import socket
from unittest.mock import AsyncMock, patch

import pytest

from jvcprojector.connection import resolve
from jvcprojector.error import JvcProjectorConnectError


@pytest.mark.asyncio
@pytest.mark.parametrize("host", ["projector.local", "192.168.1.100"])
async def test_resolve_hostname_or_ip_uses_first_ipv4(host):
    """Both hostname and literal-IP lookups constrain the system resolver to IPv4."""
    addresses = [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("192.168.1.100", 0),
        ),
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("192.168.1.101", 0),
        ),
    ]
    with patch.object(
        asyncio.get_running_loop(), "getaddrinfo", new=AsyncMock(return_value=addresses)
    ) as lookup:
        assert await resolve(host) == "192.168.1.100"
    lookup.assert_awaited_once_with(
        host, None, family=socket.AF_INET, type=socket.SOCK_STREAM
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        socket.gaierror(socket.EAI_NONAME, "Unknown hostname"),
        OSError("Resolver unavailable"),
    ],
)
async def test_resolve_wraps_system_resolution_errors(error):
    """Resolver failures retain their cause and use the library error contract."""
    with (
        patch.object(
            asyncio.get_running_loop(), "getaddrinfo", new=AsyncMock(side_effect=error)
        ),
        pytest.raises(
            JvcProjectorConnectError, match="Failed to resolve host projector.invalid"
        ) as raised,
    ):
        await resolve("projector.invalid")
    assert raised.value.__cause__ is error


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "addresses",
    [
        [],
        [
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("::1", 0, 0, 0),
            )
        ],
    ],
)
async def test_resolve_rejects_empty_or_non_ipv4_result(addresses):
    """A response without IPv4 addresses must never become an indexing error."""
    with (
        patch.object(
            asyncio.get_running_loop(),
            "getaddrinfo",
            new=AsyncMock(return_value=addresses),
        ),
        pytest.raises(JvcProjectorConnectError, match="No IPv4 addresses"),
    ):
        await resolve("projector.local")
