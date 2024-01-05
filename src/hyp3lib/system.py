"""Utilities for probing the processing system"""

import datetime
import logging
import os
import subprocess


def gamma_version():
    """Probe the system to find the version of GAMMA installed, if possible"""
    gamma_ver = os.getenv('GAMMA_VERSION')
    if gamma_ver is None:
        try:
            gamma_home = os.environ['GAMMA_HOME']
        except KeyError:
            logging.error('No GAMMA_VERSION or GAMMA_HOME environment variables defined! GAMMA is not installed.')
            raise

        try:
            with open(f"{gamma_home}/ASF_Gamma_version.txt") as f:
                gamma_ver = f.readlines()[-1].strip()
        except IOError:
            logging.warning(
                f"No GAMMA_VERSION environment variable or ASF_Gamma_version.txt "
                f"file found in GAMMA_HOME:\n     {os.getenv('GAMMA_HOME')}\n"
                f"Attempting to parse GAMMA version from its install directory"
            )
            gamma_ver = os.path.basename(gamma_home).split('-')[-1]
    try:
        datetime.datetime.strptime(gamma_ver, '%Y%m%d')
    except ValueError:
        logging.warning(f'GAMMA version {gamma_ver} does not conform to the expected YYYYMMDD format')

    return gamma_ver


def isce_version():
    """Probe the system to find the version of ISCE installed, if possible"""
    # NOTE: ISCE does not consistently provide version numbers. For example, the
    #       self reported version of ISCE with the conda install of ISCE 2.4.1
    #       is 2.3 (import isce; isce.__version__).
    try:
        import isce
    except ImportError:
        logging.error('ISCE is not installed.')
        raise

    # prefer the conda reported version number; requires shell for active conda env
    version = subprocess.check_output('conda list | grep isce | awk \'{print $2}\'', shell=True, text=True)
    if version:
        return version.strip()

    try:
        version = isce.__version__
        return version
    except AttributeError:
        logging.warning('ISCE does not have a version attribute.')
        return None
