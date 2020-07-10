"""Creates a Cloud Optimized GeoTIFF from the input GeoTIFF(s)"""

import argparse
import logging
import os
import shutil
import sys
from glob import glob
from tempfile import NamedTemporaryFile

from osgeo import gdal


def cogify_dir(directory: str, file_pattern: str = '*.tif'):
    """
    Convert all found GeoTIFF files to a Cloud Optimized GeoTIFF inplace
    Args:
        directory: directory to search through
        file_pattern: the pattern for finding GeoTIFFs
    """
    path_expression = os.path.join(directory, file_pattern)
    logging.info(f'Converting files to COGs for {path_expression}')
    for filename in glob(path_expression):
        cogify_file(filename)


def cogify_file(filename: str):
    """
    Convert a GeoTIFF to a Cloud Optimized GeoTIFF inplace

    Args:
        filename: GeoTIFF file to convert
    """
    logging.info(f'Converting {filename} to COG')
    creation_options = ['TILED=YES', 'COMPRESS=DEFLATE']
    with NamedTemporaryFile() as temp_file:
        shutil.copy(filename, temp_file.name)
        gdal.Translate(filename, temp_file.name, format='GTiff', creationOptions=creation_options, noData=0)


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
