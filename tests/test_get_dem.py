from filecmp import cmp

import pytest

from hyp3lib import DemError
from hyp3lib.get_dem import get_dem, get_best_dem


def test_get_best_dem():
    # atlantic ocean, south of western africa
    with pytest.raises(DemError):
        get_best_dem(y_min=0, y_max=1, x_min=0, x_max=1)

    # utah, western united states
    (name, projection, tile_list, poly_list) = get_best_dem(y_min=38.2, y_max=38.8, x_min=-110.8, x_max=-110.2)
    assert name == 'NED13'
    assert projection == 4269
    assert tile_list == ['n39w111']
    assert poly_list == ['POLYGON ((-111.000556 39.000556,-109.999444888884 39.000556,-109.999444888884 37.9994448888845,-111.000556 37.9994448888845,-111.000556 39.000556))']

    # democratic republic of the congo, southern africa
    (name, projection, tile_list, poly_list) = get_best_dem(y_min=-6.8, y_max=-6.2, x_min=27.2, x_max=27.8)
    assert name == 'SRTMGL1'
    assert projection == 4326
    assert tile_list == ['S07E027']
    assert poly_list == ['POLYGON ((26.999861 -5.999861,28.0001387777858 -5.999861,28.0001387777858 -7.00013877778578,26.999861 -7.00013877778578,26.999861 -5.999861))']


def test_get_dem(tmp_path, golden_dem):
    with pytest.raises(DemError):
        get_dem(y_min=0, y_max=1, x_min=0, x_max=1, outfile='dem.tif', post=30.0)

    output_file = tmp_path / 'dem.tif'
    name = get_dem(y_min=-6.8, y_max=-6.79, x_min=27.79, x_max=27.8, outfile=str(output_file), post=30.0)
    assert name == 'SRTMGL1'
    assert output_file.exists()
    assert cmp(output_file, golden_dem)
