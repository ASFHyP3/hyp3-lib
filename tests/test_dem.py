import json

import pytest

from hyp3lib import DemError, dem


# def test_get_best_dem():
#     assert dem.get_best_dem(y_min=37.0, y_max=38.0, x_min=-118.0, x_max=-117.0) == 'COP30'
#     assert dem.get_best_dem(y_min=-6.8, y_max=-6.2, x_min=27.2, x_max=27.8) == 'SRTMGL1'
#     assert dem.get_best_dem(y_min=59.975, y_max=60.1, x_min=99.5, x_max=100.5) == 'COP30'
#     assert dem.get_best_dem(y_min=59.976, y_max=60.1, x_min=99.5, x_max=100.5) == 'COP30'
#
#     with pytest.raises(DemError):
#         dem.get_best_dem(y_min=0, y_max=1, x_min=0, x_max=1)


def test_get_polygon_from_manifest(test_data_folder):
    manifest_file = test_data_folder / 'test.SAFE' / 'manifest.safe'
    polygon = dem.get_polygon_from_manifest(str(manifest_file))
    assert polygon.ExportToWkt() == 'POLYGON ((-111.577644 37.063725,-114.392342 37.459259,-114.048729 39.136841,' \
                                    '-111.166084 38.742691,-111.577644 37.063725))'


def test_utm_from_lat_lon():
    assert dem.utm_from_lon_lat(0, 0) == 32631
    assert dem.utm_from_lon_lat(-179, -1) == 32701
    assert dem.utm_from_lon_lat(179, 1) == 32660
    assert dem.utm_from_lon_lat(27, 89) == 32635
    assert dem.utm_from_lon_lat(182, 1) == 32601
    assert dem.utm_from_lon_lat(-182, 1) == 32660
    assert dem.utm_from_lon_lat(-360, -1) == 32731


def test_get_coverage_geometry(tmp_path):
    coverage_file = tmp_path / 'coverage.geojson'
    geojson = {
        "type": "FeatureCollection",
        'features': [
            {
                'type': 'Feature',
                'geometry': {
                  'type': 'Point',
                  'coordinates': [125.6, 10.1],
                },
            },
        ],
    }
    with open(coverage_file, 'w') as f:
        json.dump(geojson, f)

    geom = dem.get_coverage_geometry(str(coverage_file))
    assert geom.ExportToWkt() == 'POINT (125.6 10.1)'


# def test_get_best_dem_antimeridian():
#     # aleutian islands
#     name, projection, tile_list, wkt_list = get_best_dem(y_min=51.3, y_max=51.7, x_min=-179.5, x_max=179.5)
#     assert name == 'SRTMGL1'
#     assert projection == 4326
#     assert len(tile_list) == 241
#     for tile in tile_list:
#         assert tile.startswith('N51')
#     assert len(wkt_list) == 241
#
#
# def test_get_best_dem_antimeridian_shifted():
#     # aleutian islands
#     name, projection, tile_list, wkt_list = get_best_dem(y_min=51.3, y_max=51.7, x_min=179.5, x_max=180.5)
#     assert name == 'SRTMGL1'
#     assert projection == 4326
#     assert tile_list == ['N51E179', 'N51W180']
#     assert wkt_list == [
#         'POLYGON ((178.999861 52.000139,180.000138777786 52.000139,180.000138777786 50.9998612222142,'
#         '178.999861 50.9998612222142,178.999861 52.000139))',
#         'POLYGON ((179.999861 52.000139,181.000138777786 52.000139,181.000138777786 50.9998612222142,'
#         '179.999861 50.9998612222142,179.999861 52.000139))',
#     ]
