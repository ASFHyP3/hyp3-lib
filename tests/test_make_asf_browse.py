import logging
import os

from PIL import Image

from hyp3lib.makeAsfBrowse import makeAsfBrowse


def test_width_smaller(geotiff):
    geotiff_base = geotiff.replace('.tif', '')
    browse_width = makeAsfBrowse(geotiff, geotiff_base, width=100)

    assert browse_width == 100

    assert os.path.exists(f'{geotiff_base}.png')
    assert os.path.exists(f'{geotiff_base}.png.aux.xml')
    assert os.path.exists(f'{geotiff_base}.kmz')

    with Image.open(geotiff.replace('.tif', '.png')) as png:
        assert png.size[0] == browse_width


def test_width_larger(geotiff, caplog):
    geotiff_base = geotiff.replace('.tif', '')

    with caplog.at_level(logging.DEBUG):
        browse_width = makeAsfBrowse(geotiff, geotiff_base)

        assert os.path.exists(f'{geotiff_base}.png')
        assert os.path.exists(f'{geotiff_base}.png.aux.xml')
        assert os.path.exists(f'{geotiff_base}.kmz')

        assert 'Using GeoTIFF width' in caplog.text

        with Image.open(f'{geotiff_base}.png') as png:
            assert png.size[0] == browse_width
