"""Creates a Cloud Optimized GeoTIFF from the input GeoTIFF(s)"""

import argparse
import logging
import os
import sys

from hyp3lib.image.tiff import cogify_file


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('geotiffs', nargs='+', help='name of GeoTIFF file(s)')
    args = parser.parse_args()

    out = logging.StreamHandler(stream=sys.stdout)
    out.addFilter(lambda record: record.levelno <= logging.INFO)
    err = logging.StreamHandler()
    err.setLevel(logging.WARNING)
    logging.basicConfig(format='%(message)s', level=logging.INFO, handlers=(out, err))

    for geotiff_file in args.geotiffs:
        cogify_file(geotiff_file)


if __name__ == '__main__':
    main()
