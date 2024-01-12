"""Common library for HyP3 plugins"""

from importlib.metadata import version

from hyp3lib.exceptions import (
    DemError,
    ExecuteError,
    GeometryError,
    GranuleError,
    OrbitDownloadError,
)

__version__ = version(__name__)

__all__ = [
    '__version__',
    'DemError',
    'ExecuteError',
    'GeometryError',
    'GranuleError',
    'OrbitDownloadError',
]
