from filecmp import cmp
from os import chdir

import pytest

from hyp3lib import DemError
from hyp3lib.get_dem import get_dem, get_best_dem


def test_get_best_dem():
    # atlantic ocean, south of western africa
    with pytest.raises(DemError):
        get_best_dem(y_min=0, y_max=1, x_min=0, x_max=1)

    # utah, western united states
    (name, projection, tile_list, wkt_list) = get_best_dem(y_min=38.2, y_max=38.8, x_min=-110.8, x_max=-110.2)
    assert name == 'NED13'
    assert projection == 4269
    assert tile_list == ['n39w111']
    assert wkt_list == ['POLYGON ((-111.000556 39.000556,-109.999444888884 39.000556,-109.999444888884 37.9994448888845,-111.000556 37.9994448888845,-111.000556 39.000556))']

    # democratic republic of the congo, southern africa
    (name, projection, tile_list, wkt_list) = get_best_dem(y_min=-6.8, y_max=-6.2, x_min=27.2, x_max=27.8)
    assert name == 'SRTMGL1'
    assert projection == 4326
    assert tile_list == ['S07E027']
    assert wkt_list == ['POLYGON ((26.999861 -5.999861,28.0001387777858 -5.999861,28.0001387777858 -7.00013877778578,26.999861 -7.00013877778578,26.999861 -5.999861))']

    # alaska
    (name, projection, tile_list, wkt_list) = get_best_dem(y_min=67.9, y_max=68.1, x_min=-155.6, x_max=-155.4)
    assert name == 'NED2'
    assert projection == 4269
    assert tile_list == ['n68w156', 'n69w156']
    assert wkt_list == [
       'POLYGON ((-156.003333 68.003333,-154.996666333325 68.003333,-154.996666333325 66.9966663333253,-156.003333 66.9966663333253,-156.003333 68.003333))',
       'POLYGON ((-156.003333 69.003333,-154.996666333325 69.003333,-154.996666333325 67.9966663333253,-156.003333 67.9966663333253,-156.003333 69.003333))',
    ]

    # northern russia, just missing coverage threshold
    with pytest.raises(DemError):
        get_best_dem(y_min=59.976, y_max=60.1, x_min=99.5, x_max=100.5)

    # northern russia, just passing coverage threshold
    (name, projection, tile_list, wkt_list) = get_best_dem(y_min=59.975, y_max=60.1, x_min=99.5, x_max=100.5)
    assert name == 'SRTMGL1'
    assert projection == 4326
    assert tile_list == ['N59E099', 'N59E100']
    assert wkt_list == [
        'POLYGON ((98.999861 60.000139,100.000138777786 60.000139,100.000138777786 58.9998612222142,98.999861 58.9998612222142,98.999861 60.000139))',
        'POLYGON ((99.999861 60.000139,101.000138777786 60.000139,101.000138777786 58.9998612222142,99.999861 58.9998612222142,99.999861 60.000139))',
    ]


def test_get_dem(tmp_path, golden_dem):
    with pytest.raises(DemError):
        get_dem(y_min=0, y_max=1, x_min=0, x_max=1, outfile='dem.tif', post=30.0)

    chdir(tmp_path)
    output_file = tmp_path / 'dem.tif'
    name = get_dem(y_min=-6.8, y_max=-6.79, x_min=27.79, x_max=27.8, outfile=str(output_file), post=30.0)
    assert name == 'SRTMGL1'
    assert output_file.exists()
    assert cmp(output_file, golden_dem)
