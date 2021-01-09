"""Get a DEM file in .tif format from the ASF DEM heap"""

import json
import logging
from pathlib import Path
from typing import List, Tuple

import jinja2
from lxml import etree
from osgeo import gdal, ogr

import hyp3lib.etc
from hyp3lib import DemError

gdal.UseExceptions()
ogr.UseExceptions()


def build_geojson(gdal_info: List[dict]) -> dict:
    features = [
        {
            'type': 'Feature',
            'properties': {},
            'id': 0,
            'geometry': tile['wgs84Extent']
        }
        for tile in gdal_info
    ]

    geojson = {
        'type': 'FeatureCollection',
        'crs': {
            'type': 'name',
            'properties': {
                'name': 'EPSG:4326'
            }
        },
        'features': features
    }
    return geojson


def build_vrt(gdal_info: List[dict]) -> str:
    pixel_width = min([abs(item['geoTransform'][1]) for item in gdal_info])
    pixel_height = min([abs(item['geoTransform'][5]) for item in gdal_info])
    min_x = min([item['geoTransform'][0] for item in gdal_info])
    max_x = max([item['cornerCoordinates']['lowerRight'][0] for item in gdal_info])
    min_y = min([item['cornerCoordinates']['lowerRight'][1] for item in gdal_info])
    max_y = max([item['geoTransform'][3] for item in gdal_info])

    payload = {
        'pixel_width': pixel_width,
        'pixel_height': pixel_height,
        'min_x': min_x,
        'max_y': max_y,
        'raster_width': round((max_x - min_x) / pixel_width + 1),
        'raster_height': round((max_y - min_y) / pixel_height + 1),
        # assumed to be the same across all tiles
        'projection_wkt': gdal_info[0]['coordinateSystem']['wkt'].replace('\n', ''),
        'axis_mapping': gdal_info[0]['coordinateSystem']['dataAxisToSRSAxisMapping'],
        'area_or_point': gdal_info[0]['metadata'][''].get('AREA_OR_POINT'),
        'data_type': gdal_info[0]['bands'][0]['type'],
        'color_interp': gdal_info[0]['bands'][0]['colorInterpretation'],
        'no_data_value': gdal_info[0]['bands'][0].get('noDataValue'),
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
            } for tile in gdal_info
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


def get_dem_config():
    try:
        config_file = Path.home() / '.hyp3' / 'dems.json'
        with open(config_file) as f:
            dem_list = json.load(f)
    except FileNotFoundError:
        config_file = Path(hyp3lib.etc.__file__).parent / 'config' / 'dems.json'
        with open(config_file) as f:
            dem_list = json.load(f)
    return dem_list


def get_polygon_from_manifest(manifest_file: str) -> ogr.Geometry:
    root = etree.parse(manifest_file)
    coordinates_string = root.find('//gml:coordinates', namespaces={'gml': 'http://www.opengis.net/gml'}).text
    points = [point.split(',') for point in coordinates_string.split(' ')]
    points.append(points[0])
    wkt = ','.join([f'{p[1]} {p[0]}' for p in points])
    wkt = f'POLYGON(({wkt}))'
    return ogr.CreateGeometryFromWkt(wkt)


def get_coverage_geometry(coverage_geojson):
    ds = ogr.Open(coverage_geojson)
    layer = ds.GetLayer()
    geom = None
    for feature in layer:
        geom = feature.GetGeometryRef()
        break
    del ds
    return ogr.CreateGeometryFromWkt(geom.ExportToWkt())


def get_best_dem(polygon: ogr.Geometry, threshold: float = 0.2) -> str:
    dem_config = get_dem_config()
    best_pct = 0
    best_dem = ''
    for dem_name in dem_config:
        coverage = get_coverage_geometry(dem_config[dem_name]['coverage'])

        covered_area = polygon.Intersection(coverage).GetArea()
        total_area = polygon.GetArea()
        pct = covered_area / total_area
        logging.debug(f"{dem_name}: {pct*100:.2f}% coverage ({covered_area:.2f}/{total_area:.2f})")

        if best_pct == 0 or pct > best_pct + 0.05:
            best_pct = pct
            best_dem = dem_name

    if best_pct < threshold:
        raise DemError('Unable to find a DEM file for that area')

    return best_dem


def utm_from_lon_lat(lon: float, lat: float) -> int:
    hemisphere = 32600 if lat >= 0 else 32700
    zone = int(lon // 6 + 30) % 60 + 1
    return hemisphere + zone


def subset_dem(polygon: ogr.Geometry, output_file: str, dem_name: str, buffer: float = 0.15,
               pixel_size: float = 30.0) -> str:
    dem_config = get_dem_config()
    vrt = dem_config[dem_name]['vrt']

    min_x, max_x, min_y, max_y = polygon.Buffer(buffer).GetEnvelope()
    output_bounds = (min_x, min_y, max_x, max_y)

    centroid = polygon.Centroid()
    epsg_code = utm_from_lon_lat(centroid.GetX(), centroid.GetY())

    gdal.Warp(output_file, vrt, outputBounds=output_bounds, outputBoundsSRS='EPSG:4326', dstSRS=f'EPSG:{epsg_code}',
              xRes=pixel_size, yRes=pixel_size, targetAlignedPixels=True, resampleAlg='cubic', multithread=True)

    #TODO pixel as point?

    return output_file


def subset_dem_for_rtc(output_file: str, manifest_file: str, pixel_size: float = 30.0) -> Tuple[str, str]:
    polygon = get_polygon_from_manifest(manifest_file)
    # TODO deal with antimeridian

    dem_name = get_best_dem(polygon, threshold=0.2)
    dem_tiff = subset_dem(polygon, output_file, dem_name, buffer=0.15, pixel_size=pixel_size)
    return dem_tiff, dem_name
