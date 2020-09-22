"""Resamples a GeoTIFF file to make a KML and a PNG browse image for ASF"""

import argparse
import logging
import os
import sys

from hyp3lib.image import create_browse as makeAsfBrowse

def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('geotiff', help='name of GeoTIFF file to resample')
    parser.add_argument('basename', help='base name of output files')
    parser.add_argument('-n', '--nearest-neighbor', action='store_true',
                        help="use GDAL's GRIORA_NearestNeighbour interpolation instead"
                             " of GRIORA_Cubic to resample the GeoTIFF")
    parser.add_argument('-w', '--width', default=2048,
                        help='browse image width')
    args = parser.parse_args()

    out = logging.StreamHandler(stream=sys.stdout)
    out.addFilter(lambda record: record.levelno <= logging.INFO)
    err = logging.StreamHandler()
    err.setLevel(logging.WARNING)
    logging.basicConfig(format='%(message)s', level=logging.INFO, handlers=(out, err))

    if not os.path.exists(args.geotiff):
        parser.error(f'GeoTIFF file {args.geotiff} does not exist!')
    if os.path.splitext(args.basename)[-1]:
        parser.error(f'Output file {args.basename} has an extension!')

    makeAsfBrowse(
        args.geotiff, args.basename, use_nn=args.nearest_neighbor, width=args.width
    )


if __name__ == '__main__':
    main()
