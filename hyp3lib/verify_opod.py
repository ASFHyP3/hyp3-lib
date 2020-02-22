#!/usr/bin/env python
"""Read OPOD State Vector"""

from __future__ import print_function, absolute_import, division, unicode_literals

from lxml import etree
import argparse
import logging
import os
import sys

def verify_opod(fi):
    logging.info("Verifying state vector file")
    root = etree.parse(fi)
    for item in root.iter('File_Description'):
         if "Orbit File" not in item.text:
             logging.error("Not an orbit file!")
             exit(1)
         else:
             logging.info("...Found orbit file")
    for item in root.iter('File_Type'):
         if "AUX_POEORB" not in item.text and "AUX_PREORB" not in item.text and "AUX_RESORB" not in item.text:
             logging.error("Unknown file type!")
             exit(1)
         else:
             logging.info("...Found file type {}".format(item.text))
    logging.info("State vector file verified")


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument("OPODfile",help="S1 OPOD file")
    args = parser.parse_args()

    logFile = "OPOD_{}.log".format(os.getpid())
    logging.basicConfig(filename=logFile,format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',level=logging.DEBUG)
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.info("Starting run")

    verify_opod(args.OPODfile)


if __name__ == '__main__':
    main()
