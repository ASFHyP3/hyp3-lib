"""Resamples a GeoTIFF file to make a KML and a PNG browse image for ASF"""

import argparse
import os

from hyp3lib import saa_func_lib as saa
from hyp3lib.resample_geotiff import resample_geotiff


def makeAsfBrowse(geotiff: str, base_name: str, use_nn=False):
    """
    Make a 2048 KML and PNG browse image for ASF
    Args:
        geotiff: name of GeoTIFF file
        base_name: base name of output files
        use_nn: Use GDAL's GRIORA_NearestNeighbour interpolation instead of GRIORA_Cubic
            to resample the GeoTIFF
    """
    tiff_x_res, _, _, _ = saa.read_gdal_file_geo(saa.open_gdal_file(geotiff))
    if tiff_x_res < 2048:
        print("Warning: width exceeds image dimension - using actual value")
        resolution = tiff_x_res
    else:
        resolution = 2048

    resample_geotiff(geotiff, resolution, "KML", f'{base_name}.kmz', use_nn)
    resample_geotiff(geotiff, resolution, "PNG", f'{base_name}.png', use_nn)


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('geotiff', help='name of GeoTIFF file to resample')
    parser.add_argument('basename', help='base name of output files')
    parser.add_argument('-n', '--nearest-neighbor', action='store_true',
                        help="Use GDAL's GRIORA_NearestNeighbour interpolation instead"
                             " of GRIORA_Cubic to resample the GeoTIFF")
    args = parser.parse_args()

    if not os.path.exists(args.geotiff):
        parser.error(f'GeoTIFF file {args.geotiff} does not exist!')
    if os.path.splitext(args.basename)[-1]:
        parser.error(f'Output file {args.basename} has an extension!')

    makeAsfBrowse(args.geotiff, args.basename, use_nn=args.nearest_neighbor)


if __name__ == '__main__':
    main()
