"""Common library for HyP3 plugins"""

# FIXME: Python 3.8+ this should be `from importlib.metadata...`
from importlib_metadata import PackageNotFoundError, version

from hyp3lib.exceptions import (
    DemError,
    ExecuteError,
    GeometryError,
    GranuleError,
    OrbitDownloadError,
)

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    print(f'{__name__} package is not installed!\n'
          f'Install in editable/develop mode via (from the top of this repo):\n'
          f'   python -m pip install -e .[develop]\n'
          f'Or, to just get the version number use:\n'
          f'   python setup.py --version')

__all__ = [
    '__version__',
    'DemError',
    'ExecuteError',
    'GeometryError',
    'GranuleError',
    'OrbitDownloadError',
]
