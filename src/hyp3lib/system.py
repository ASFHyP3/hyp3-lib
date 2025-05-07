"""Utilities for probing the processing system"""

import logging
import subprocess


def isce_version():
    """Probe the system to find the version of ISCE installed, if possible"""
    # NOTE: ISCE does not consistently provide version numbers. For example, the
    #       self reported version of ISCE with the conda install of ISCE 2.4.1
    #       is 2.3 (import isce; isce.__version__).
    try:
        import isce  # type: ignore[import-not-found]
    except ImportError:
        logging.error('ISCE is not installed.')
        raise

    # prefer the conda reported version number; requires shell for active conda env
    version = subprocess.check_output("conda list | grep isce | awk '{print $2}'", shell=True, text=True)
    if version:
        return version.strip()

    try:
        version = isce.__version__
        return version
    except AttributeError:
        logging.warning('ISCE does not have a version attribute.')
        return None
