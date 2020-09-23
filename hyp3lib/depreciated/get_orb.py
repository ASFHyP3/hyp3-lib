"""Get Sentinel-1 orbit file(s) from ASF or ESA website"""

import argparse
import logging
import os
import sys

from hyp3lib import OrbitDownloadError
from hyp3lib.orbits import downloadSentinelOrbitFile


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('safe_files', help='Sentinel-1 SAFE file name(s)', nargs="*")
    parser.add_argument('-p', '--provider', nargs='*', default=['ESA', 'ASF'],  choices=['ESA', 'ASF'],
                        help="Name(s) of the orbit file providers' organization, in order of preference")
    parser.add_argument('-t', '--orbit-types', nargs='*', default=['AUX_POEORB', 'AUX_RESORB'],
                        choices=['MPL_ORBPRE', 'AUX_POEORB', 'AUX_PREORB', 'AUX_RESORB', 'AUX_RESATT'],
                        help="Name(s) of the orbit file providers' organization, in order of preference. "
                             "See https://qc.sentinel1.eo.esa.int/")
    parser.add_argument('-d', '--directory', default=os.getcwd(), help='Download files to this directory')
    args = parser.parse_args()

    out = logging.StreamHandler(stream=sys.stdout)
    out.addFilter(lambda record: record.levelno <= logging.INFO)
    err = logging.StreamHandler()
    err.setLevel(logging.WARNING)
    logging.basicConfig(format='%(message)s', level=logging.INFO, handlers=(out, err))

    for safe in args.safe_files:
        try:
            orbit_file, provided_by = downloadSentinelOrbitFile(
                safe, directory=args.directory, providers=args.provider, orbit_types=args.orbit_types
            )
            logging.info("Downloaded orbit file {} from {}".format(orbit_file, provided_by))
        except OrbitDownloadError as e:
            logging.warning(f'WARNING: unable to download orbit file for {safe}\n    {e}')


if __name__ == "__main__":
    main()
