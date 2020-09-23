import logging
import os

from PIL import Image
from osgeo import gdal

from hyp3lib.image import image


def test_create_thumbnail(png_image):
    with Image.open(png_image) as input_image:
        assert input_image.size == (162, 150)

    thumbnail = image.create_thumbnail(png_image, (100, 100))
    assert thumbnail.name == 'test_thumb.png'

    with Image.open(png_image) as input_image:
        assert input_image.size == (162, 150)

    with Image.open(thumbnail) as output_image:
        assert output_image.size == (100, 93)

    thumbnail = image.create_thumbnail(png_image, (255, 255))

    with Image.open(thumbnail) as output_image:
        assert output_image.size == (162, 150)


def test_create_browse_width_smaller(geotiff):
    geotiff_base = geotiff.replace('.tif', '')
    browse_width = image.create_browse(geotiff, geotiff_base, width=10)

    assert browse_width == 10
    with Image.open(f'{geotiff_base}.png') as png:
        assert png.size[0] == browse_width

    assert os.path.exists(f'{geotiff_base}.png.aux.xml')
    assert os.path.exists(f'{geotiff_base}.kmz')


def test_create_browse_width_larger(geotiff, caplog):
    tiff = gdal.Open(geotiff)
    tiff_width = tiff.RasterXSize
    tiff = None  # How to close with gdal

    geotiff_base = geotiff.replace('.tif', '')

    with caplog.at_level(logging.DEBUG):
        browse_width = image.create_browse(geotiff, geotiff_base, width=2048)

        assert browse_width == tiff_width
        assert 'Using GeoTIFF width' in caplog.text
        with Image.open(f'{geotiff_base}.png') as png:
            assert png.size[0] == tiff_width