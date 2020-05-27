"""Utilities for metadata manipulation"""

import datetime
import os
import logging
from pathlib import Path
from typing import Union

from hyp3lib import GranuleError


def add_esa_citation(granule: str, dir_: Union[str, Path]):
    """Add an ESA citation for S1 Granules

    Args:
        granule: The name of the granule
        dir_: The directory to add the citation file to
    """

    if not granule.startswith('S1'):
        raise GranuleError

    y = int(datetime.datetime.now().year)
    ay = None
    for subdir, dirs, files in os.walk(dir_):
        for f in files:
            try:
                for item in f.split("_"):
                    if item[0:8].isdigit() and item[8] == "T" and item[9:15].isdigit():
                        ay = item[0:4]
                        break
            except:
                logging.error("ERROR: Unable to determine acquisition year from filename {f}".format(f=f))
            if ay:
                break
        if ay:
            break

    if ay is None:
        ay = y

    with open(os.path.join(dir_, 'ESA_citation.txt'), 'w') as f:
        f.write('ASF DAAC {0}, contains modified Copernicus Sentinel data {1}, processed by ESA.'.format(y,ay))
