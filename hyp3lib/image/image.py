"""Tools for working with images"""
import logging

from PIL import Image
from typing import Tuple
from pathlib import Path

from osgeo import gdal

from hyp3lib.image.tiff import resample_geotiff


def create_thumbnail(input_image: Path, size: Tuple[int, int] = (100, 100), output_dir: Path = None) -> Path:
    """Create a thumbnail from an image

    Args:
        input_image: location of the input image
        size: size of the thumbnail to create
        output_dir: if provided create the thumbnail here, otherwise create it alongside the input image

    Returns:
        thumbnail: location of the created thumbnail
    """
    thumbnail_name = f'{input_image.stem}_thumb{input_image.suffix}'
    if output_dir is None:
        thumbnail = input_image.with_name(thumbnail_name)
    else:
        thumbnail = output_dir / thumbnail_name

    output_image = Image.open(input_image)
    output_image.thumbnail(size)
    output_image.save(thumbnail)
    return thumbnail


def create_browse(geotiff: str, base_name: str, use_nn=False, width: int = 2048):
    """
    Make a KML and PNG browse image for ASF
    Args:
        geotiff: name of GeoTIFF file
        base_name: base name of output files
        use_nn: Use GDAL's GRIORA_NearestNeighbour interpolation instead of GRIORA_Cubic
            to resample the GeoTIFF
        width: browse image width

    Returns:
        browse_width: the width of the created browse image
    """
    tiff = gdal.Open(geotiff)
    tiff_width = tiff.RasterXSize
    tiff = None  # How to close with gdal

    if tiff_width < width:
        logging.warning(f'Requested image dimension of {width} exceeds GeoTIFF width {tiff_width}.'
                        f' Using GeoTIFF width')
        browse_width = tiff_width
    else:
        browse_width = width

    resample_geotiff(geotiff, browse_width, 'KML', f'{base_name}.kmz', use_nn)
    resample_geotiff(geotiff, browse_width, 'PNG', f'{base_name}.png', use_nn)

    return browse_width
