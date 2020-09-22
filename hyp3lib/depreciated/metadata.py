"""Utilities for metadata manipulation"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Union

from hyp3lib import GranuleError


def add_esa_citation(granule: str, directory: Union[str, Path]):
    """Add an ESA citation file for S1 Granules

    Args:
        granule: The name of the granule
        directory: The directory to add the citation file to
    """

    if not granule.startswith('S1'):
        raise GranuleError(f'ESA citation only valid for S1 granules, not: {granule}')

    current_year = datetime.now().year
    try:
        timestamp = re.search(r'\d{8}T\d{6}', granule)[0]
        aq_year = datetime.strptime(timestamp, '%Y%m%dT%H%M%S').year
    except (TypeError, ValueError):
        raise GranuleError(f'Unable to determine acquisition year from: {granule}')

    with open(os.path.join(directory, 'ESA_citation.txt'), 'w') as f:
        f.write(f'ASF DAAC {current_year}, contains modified Copernicus Sentinel data {aq_year}, processed by ESA.\n')
