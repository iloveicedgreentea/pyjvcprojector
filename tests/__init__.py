"""pytest tests"""

from jvcprojector.device import END

IP = "127.0.0.1"
HOST = "localhost"
PORT = 12345
TIMEOUT = 3.0
MAC = "abcd1234"
MODEL = "model123"
PASSWORD = "pass1234"


def cc(hdr: bytes, cmd: str):
    """Create a command."""
    return hdr + cmd.encode() + END
