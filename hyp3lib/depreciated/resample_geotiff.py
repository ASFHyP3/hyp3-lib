"""Resamples a GeoTIFF file and saves it in a number of formats"""

import argparse
import os

from hyp3lib.image import resample_geotiff


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('geotiff', help='name of GeoTIFF file (input)')
    parser.add_argument('width', help='target width (input)')
    parser.add_argument('format', help='output format: GeoTIFF, JPEG, PNG, KML')
    parser.add_argument('output', help='name of output file (output)')
    args = parser.parse_args()

    if not os.path.exists(args.geotiff):
        parser.error(f'GeoTIFF file {args.geotiff} does not exist!')
    if not os.path.splitext(args.output)[-1]:
        parser.error(f'Output file {args.output} does not have an extension!')

    resample_geotiff(args.geotiff, args.width, args.format, args.output)


if __name__ == '__main__':
    main()

