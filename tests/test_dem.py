import json
from pathlib import Path

import pytest
from osgeo import gdal, ogr

from hyp3lib import DemError, dem


def test_intersects_dem():
    geojson = {
        'type': 'Point',
        'coordinates': [169, -45],
    }
    geometry = ogr.CreateGeometryFromJson(json.dumps(geojson))
    assert dem._intersects_dem(geometry)

    geojson = {
        'type': 'Point',
        'coordinates': [0, 0],
    }
    geometry = ogr.CreateGeometryFromJson(json.dumps(geojson))
    assert not dem._intersects_dem(geometry)


def test_get_file_paths():
    geojson = {
        'type': 'Point',
        'coordinates': [0, 0],
    }
    geometry = ogr.CreateGeometryFromJson(json.dumps(geojson))
    assert dem._get_dem_file_paths(geometry) == []

    geojson = {
        'type': 'Point',
        'coordinates': [169, -45],
    }
    geometry = ogr.CreateGeometryFromJson(json.dumps(geojson))
    assert dem._get_dem_file_paths(geometry) == [
        '/vsicurl/https://asf-dem-west.s3.amazonaws.com/v2/COP30/2021/'
        'Copernicus_DSM_COG_10_S46_00_E169_00_DEM/Copernicus_DSM_COG_10_S46_00_E169_00_DEM.tif'
    ]

    geojson = {
        'type': 'MultiPoint',
        'coordinates': [[0, 0], [169, -45], [-121.5, 73.5]],
    }
    geometry = ogr.CreateGeometryFromJson(json.dumps(geojson))
    assert dem._get_dem_file_paths(geometry) == [
        '/vsicurl/https://asf-dem-west.s3.amazonaws.com/v2/COP30/2021/'
        'Copernicus_DSM_COG_10_N73_00_W122_00_DEM/Copernicus_DSM_COG_10_N73_00_W122_00_DEM.tif',
        '/vsicurl/https://asf-dem-west.s3.amazonaws.com/v2/COP30/2021/'
        'Copernicus_DSM_COG_10_S46_00_E169_00_DEM/Copernicus_DSM_COG_10_S46_00_E169_00_DEM.tif',
    ]


def test_get_dem_features():
    assert len(list(dem._get_dem_features())) == 26475


def test_shift_for_antimeridian(tmp_path):
    file_paths = [
        '/vsicurl/https://asf-dem-west.s3.amazonaws.com/v2/COP30/2021/'
        'Copernicus_DSM_COG_10_N51_00_W180_00_DEM/Copernicus_DSM_COG_10_N51_00_W180_00_DEM.tif',
        '/vsicurl/https://asf-dem-west.s3.amazonaws.com/v2/COP30/2021/'
        'Copernicus_DSM_COG_10_N51_00_E179_00_DEM/Copernicus_DSM_COG_10_N51_00_E179_00_DEM.tif',
    ]

    with dem.GDALConfigManager(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR'):
        shifted_file_paths = dem._shift_for_antimeridian(file_paths, tmp_path)

    assert shifted_file_paths[0] == str(tmp_path / 'Copernicus_DSM_COG_10_N51_00_W180_00_DEM.vrt')
    assert shifted_file_paths[1] == file_paths[1]

    info = gdal.Info(shifted_file_paths[0], format='json')
    assert info['cornerCoordinates']['upperLeft'] == [179.9997917, 52.0001389]
    assert info['cornerCoordinates']['lowerRight'] == [180.9997917, 51.0001389]



def test_prepare_dem_geotiff_no_coverage():
    geojson = {
        'type': 'Point',
        'coordinates': [0, 0],
    }
    geometry = ogr.CreateGeometryFromJson(json.dumps(geojson))
    with pytest.raises(DemError):
        dem.prepare_dem_geotiff(Path('foo'), geometry, 30, 32601)


def test_prepare_dem_geotiff(tmp_path):
    dem_geotiff = tmp_path / 'dem.tif'
    geojson = {
        'type': 'Polygon',
        'coordinates': [
            [
                [0.4, 10.16],
                [0.4, 10.86],
                [0.6, 10.86],
                [0.6, 10.16],
                [0.4, 10.16],
            ]
        ],
    }
    geometry = ogr.CreateGeometryFromJson(json.dumps(geojson))

    dem.prepare_dem_geotiff(dem_geotiff, geometry, epsg_code=32631, pixel_size=60)
    assert dem_geotiff.exists()

    info = gdal.Info(str(dem_geotiff), format='json')
    assert info['geoTransform'] == [215040.0, 60.0, 0.0, 1201560.0, 0.0, -60.0]
    assert info['size'] == [377, 1289]


def test_prepare_dem_geotiff_antimeridian(tmp_path):
    dem_geotiff = tmp_path / 'dem.tif'
    geojson = {
        'type': 'MultiPolygon',
        'coordinates': [
            [
                [
                    [179.5, 51.4],
                    [179.5, 51.6],
                    [180.0, 51.6],
                    [180.0, 51.4],
                    [179.5, 51.4],
                ]
            ],
            [
                [
                    [-180.0, 51.4],
                    [-180.0, 51.6],
                    [-179.5, 51.6],
                    [-179.5, 51.4],
                    [-180.0, 51.4],
                ]
            ],
        ],
    }
    geometry = ogr.CreateGeometryFromJson(json.dumps(geojson))

    dem.prepare_dem_geotiff(dem_geotiff, geometry, epsg_code=32601, pixel_size=30.0)
    assert dem_geotiff.exists()

    info = gdal.Info(str(dem_geotiff), format='json')
    assert info['geoTransform'] == [291300.0, 30.0, 0.0, 5720820.0, 0.0, -30.0]
    # FIXME
    # assert info['size'] == [4780, 3897]
