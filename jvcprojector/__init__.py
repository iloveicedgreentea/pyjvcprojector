"""A python library for controlling a JVC Projector over a network connection."""

from .error import (
    JvcProjectorAuthError,
    JvcProjectorCommandError,
    JvcProjectorConnectError,
    JvcProjectorError,
)
from .projector import JvcProjector

__version__ = "1.0.6"
