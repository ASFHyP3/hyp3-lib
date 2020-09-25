import os
import shutil
import pytest
from pathlib import Path

_HERE = os.path.dirname(__file__)


@pytest.fixture(scope='session')
def safe_data(tmpdir_factory):
    safe_dir = str(tmpdir_factory.mktemp('safe_data').join('test.SAFE'))
    shutil.copytree(os.path.join(_HERE, 'data', 'test.SAFE'), safe_dir)
    return safe_dir


@pytest.fixture()
def geotiff(tmp_path):
    geotiff_file = str(tmp_path / 'test_geotiff.tif')
    shutil.copy(os.path.join(_HERE, 'data', 'test_geotiff.tif'), geotiff_file)
    return geotiff_file


@pytest.fixture()
def test_data_folder():
    return Path(_HERE) / 'data'


@pytest.fixture()
def png_image(tmp_path):
    image = tmp_path / 'test.png'
    shutil.copy(os.path.join(_HERE, 'data', 'test.png'), str(image))
    return image
