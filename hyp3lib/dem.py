"""Get a DEM file in .tif format from the ASF DEM heap"""

import json
import logging
from pathlib import Path

from osgeo import gdal, ogr

import hyp3lib.etc
from hyp3lib import DemError

gdal.UseExceptions()
ogr.UseExceptions()


def get_dem_list():
    try:
        config_file = Path.home() / '.hyp3' / 'dems.json'
        with open(config_file) as f:
            dem_list = json.load(f)
    except FileNotFoundError:
        config_file = Path(hyp3lib.etc.__file__).parent / 'config' / 'dems.json'
        with open(config_file) as f:
            dem_list = json.load(f)
    return dem_list


def get_coverage_geometry(coverage_geojson):
    ds = ogr.Open(coverage_geojson)
    layer = ds.GetLayer()
    geom = None
    for feature in layer:
        geom = feature.GetGeometryRef()
        break
    del ds
    return ogr.CreateGeometryFromWkt(geom.ExportToWkt())


def get_best_dem(y_min, y_max, x_min, x_max, threshold=0.2):
    dem_list = get_dem_list()
    wkt = f'POLYGON(({x_min} {y_min}, {x_max} {y_min}, {x_max} {y_max}, {x_min} {y_max}, {x_min} {y_min}))'
    polygon = ogr.CreateGeometryFromWkt(wkt)

    best_pct = 0
    best_dem = ''
    for dem in dem_list:
        coverage = get_coverage_geometry(dem['coverage'])

        covered_area = polygon.Intersection(coverage).GetArea()
        total_area = polygon.GetArea()
        pct = covered_area / total_area
        logging.info(f"{dem['name']}: {pct*100:.2f}% coverage ({covered_area:.2f}/{total_area:.2f})")

        if best_pct == 0 or pct > best_pct + 0.05:
            best_pct = pct
            best_dem = dem['name']

    if best_pct < threshold:
        raise DemError('Unable to find a DEM file for that area')

    return best_dem


def utm_from_lat_lon(lat, lon):
    hemisphere = 32600 if lat >= 0 else 32700
    zone = (lon // 6 + 30) % 60 + 1
    return hemisphere + zone


def get_dem(outfile, dem_name, y_min, y_max, x_min, x_max, buffer=0.0, res=30.0):
    dem_list = get_dem_list()
    vrt = [dem['vrt'] for dem in dem_list if dem['name'] == dem_name][0]
    output_bounds = [x_min - buffer, y_min - buffer, x_max + buffer, y_max + buffer]
    epsg_code = utm_from_lat_lon((y_min + y_max) / 2, (x_min + x_max) / 2)

    gdal.Warp(outfile, vrt, outputBounds=output_bounds, outputBoundsSRS='EPSG:4326', dstSRS=f'EPSG:{epsg_code}',
              xRes=res, yRes=res, targetAlignedPixels=True, resampleAlg='cubic', dstNodata=-32767, multithread=True)

    #TODO pixel as point?

    return outfile
