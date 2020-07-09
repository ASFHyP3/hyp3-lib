"""Resamples a GeoTIFF file and saves it in a number of formats"""

import argparse
import os

from hyp3lib import saa_func_lib as saa
from hyp3lib.resample_geotiff import resample_geotiff


def makeAsfBrowse(geotiff, baseName, use_nn=False):
    kmzName = baseName + ".kmz"
    pngName = baseName + ".png"
    lrgName = baseName + "_large.png"
    x1, y1, trans1, proj1 = saa.read_gdal_file_geo(saa.open_gdal_file(geotiff))
    if (x1 < 2048):
        print("Warning: width exceeds image dimension - using actual value")
        resample_geotiff(geotiff, x1, "KML", kmzName, use_nn)
        if x1 < 1024:
            resample_geotiff(geotiff, x1, "PNG", pngName, use_nn)
        else:
            resample_geotiff(geotiff, 1024, "PNG", pngName, use_nn)
        resample_geotiff(geotiff, x1, "PNG", lrgName, use_nn)
    else:
        resample_geotiff(geotiff, 2048, "KML", kmzName, use_nn)
        resample_geotiff(geotiff, 1024, "PNG", pngName, use_nn)
        resample_geotiff(geotiff, 2048, "PNG", lrgName, use_nn)


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('geotiff', help='name of GeoTIFF file (input)')
    parser.add_argument('basename', help='base name of output file (output)')
    args = parser.parse_args()

    if not os.path.exists(args.geotiff):
        parser.error(f'GeoTIFF file {args.geotiff} does not exist!')
    if os.path.splitext(args.basename)[-1]:
        parser.error(f'Output file {args.basename} has an extension!')

    makeAsfBrowse(args.geotiff, args.basename)


if __name__ == '__main__':
    main()
