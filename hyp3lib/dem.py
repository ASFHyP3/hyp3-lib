"""Get a DEM file in .tif format from the ASF DEM heap"""

import json
import logging
from pathlib import Path

import jinja2
from osgeo import gdal, ogr

import hyp3lib.etc
from hyp3lib import DemError

gdal.UseExceptions()
ogr.UseExceptions()


def build_geojson(info_list):
    features = [
        {
            "type": "Feature",
            "properties": {},
            "id": 0,
            "geometry": tile['wgs84Extent']
        }
        for tile in info_list
    ]

    geojson = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {
                "name": "EPSG:4326"
            }
        },
        "features": features
    }
    return geojson


def build_vrt(info_list):
    pixel_width = min([abs(item['geoTransform'][1]) for item in info_list])
    pixel_height = min([abs(item['geoTransform'][5]) for item in info_list])
    min_x = min([item['geoTransform'][0] for item in info_list])
    max_x = max([item['cornerCoordinates']['lowerRight'][0] for item in info_list])
    min_y = min([item['cornerCoordinates']['lowerRight'][1] for item in info_list])
    max_y = max([item['geoTransform'][3] for item in info_list])
    raster_width = round((max_x - min_x) / pixel_width + 1)
    raster_height = round((max_y - min_y) / pixel_height + 1)

    payload = {
        'pixel_width': pixel_width,
        'pixel_height': pixel_height,
        'min_x': min_x,
        'max_y': max_y,
        'raster_width': raster_width,
        'raster_height': raster_height,
        # assumed to be the same across all tiles
        'projection_wkt': info_list[0]['coordinateSystem']['wkt'].replace('\n', ''),
        'axis_mapping': info_list[0]['coordinateSystem']['dataAxisToSRSAxisMapping'],
        'area_or_point': info_list[0]['metadata'][''].get('AREA_OR_POINT'),
        'data_type': info_list[0]['bands'][0]['type'],
        'color_interp': info_list[0]['bands'][0]['colorInterpretation'],
        'no_data_value': info_list[0]['bands'][0].get('noDataValue'),
        'tiles': [
            {
                'location': tile['description'],
                'x_offset': (tile['geoTransform'][0] - min_x) / pixel_width,
                'y_offset': (max_y - tile['geoTransform'][3]) / pixel_height - 1,
                'pixel_width': abs(tile['geoTransform'][1]),
                'pixel_height': abs(tile['geoTransform'][5]),
                'width': tile['size'][0],
                'height': tile['size'][1],
                'dst_width': round(tile['size'][0] * abs(tile['geoTransform'][1]) / pixel_width),
                'dst_height': round(tile['size'][1] * abs(tile['geoTransform'][5]) / pixel_height),
                'source_band': 1,
                'block_size': tile['bands'][0]['block'],
            } for tile in info_list
        ]
    }

    template_file = Path(hyp3lib.etc.__file__).parent / 'vrt.j2'
    with open(template_file) as f:
        template_text = f.read()
    template = jinja2.Template(
        template_text,
        undefined=jinja2.StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    rendered = template.render(payload)
    return rendered


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
