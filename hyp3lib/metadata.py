"""Utilities for metadata manipulation"""

import datetime
import os
import logging


def add_citation(cfg, dir_):

    if not cfg['granule'].startswith('S1'):
        return

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
