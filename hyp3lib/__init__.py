"""Common library for HyP3 plugins"""

from __future__ import print_function, absolute_import, division, unicode_literals

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
    print('package is not installed!\n'
          'Install in editable/develop mode via (from the top of this repo):\n'
          '   pip install -e .\n'
          'Or, to just get the version number use:\n'
          '   python setup.py --version')

__all__ = [
    '__version__',
    'DemError',
    'ExecuteError',
    'GeometryError',
    'GranuleError',
    'OrbitDownloadError',
]
