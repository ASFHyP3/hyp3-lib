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

    current_year = datetime.datetime.now().year
    aq_year = None
    for subdir, dirs, files in os.walk(dir_):
        for f in files:
            try:
                for item in f.split("_"):
                    if item[0:8].isdigit() and item[8] == "T" and item[9:15].isdigit():
                        aq_year = item[0:4]
                        break
            except:
                logging.error(f"ERROR: Unable to determine acquisition year from filename {f}")
            if aq_year:
                break
        if aq_year:
            break

    if aq_year is None:
        aq_year = current_year

    with open(os.path.join(dir_, 'ESA_citation.txt'), 'w') as f:
        f.write(f'ASF DAAC {current_year}, contains modified Copernicus Sentinel data {aq_year}, processed by ESA.')
