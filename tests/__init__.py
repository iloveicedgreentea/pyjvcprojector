from jvcprojector.device import END

IP = "127.0.0.1"
PORT = 12345
TIMEOUT = 3.0
MAC = "abcd1234"
MODEL = "model123"


def cc(hdr: bytes, cmd: str):
    """Create formatted command."""
    return hdr + cmd.encode() + END
