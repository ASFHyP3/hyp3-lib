import logging
import os

from PIL import Image

from hyp3lib.makeAsfBrowse import makeAsfBrowse


def test_width_smaller(geotiff):
    browse_width = makeAsfBrowse(geotiff, geotiff.replace('.tif', ''), width=100)

    assert browse_width == 100

    assert os.path.exists(geotiff.replace('.tif', '.png'))
    assert os.path.exists(geotiff.replace('.tif', '.png.aux.xml'))
    assert os.path.exists(geotiff.replace('.tif', '.kmz'))

    with Image.open(geotiff.replace('.tif', '.png')) as png:
        assert png.size[0] == browse_width


def test_width_larger(geotiff, caplog):
    with caplog.at_level(logging.DEBUG):
        browse_width = makeAsfBrowse(geotiff, geotiff.replace('.tif', ''))

        assert os.path.exists(geotiff.replace('.tif', '.png'))
        assert os.path.exists(geotiff.replace('.tif', '.png.aux.xml'))
        assert os.path.exists(geotiff.replace('.tif', '.kmz'))

        assert 'Using GeoTIFF width' in caplog.text

        with Image.open(geotiff.replace('.tif', '.png')) as png:
            assert png.size[0] == browse_width
