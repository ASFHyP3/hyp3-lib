import json
from collections.abc import Generator
from pathlib import Path
from subprocess import PIPE, run
from tempfile import TemporaryDirectory

from lxml import etree
from osgeo import gdal, ogr, osr

from hyp3lib import DemError


DEM_GEOJSON = '/vsicurl/https://asf-dem-west.s3.amazonaws.com/v2/cop30-2021-with-cop90-us-west-2-mirror.geojson'
GEOID = '/vsicurl/https://asf-dem-west.s3.amazonaws.com/GEOID/us_nga_egm2008_1.tif'

gdal.UseExceptions()
ogr.UseExceptions()


class GDALConfigManager:
    """Context manager for setting GDAL config options temporarily"""

    def __init__(self, **options):
        """Args:
        **options: GDAL Config `option=value` keyword arguments.
        """
        self.options = options.copy()
        self._previous_options = {}

    def __enter__(self):
        for key in self.options:
            self._previous_options[key] = gdal.GetConfigOption(key)

        for key, value in self.options.items():
            gdal.SetConfigOption(key, value)

    def __exit__(self, exc_type, exc_val, exc_tb):
        for key, value in self._previous_options.items():
            gdal.SetConfigOption(key, value)


def get_geometry_from_kml(kml_file: str) -> ogr.Geometry:
    cmd = [
        'ogr2ogr',
        '-wrapdateline',
        '-datelineoffset',
        '20',
        '-f',
        'GeoJSON',
        '-mapfieldtype',
        'DateTime=String',
        '/vsistdout',
        kml_file,
    ]
    geojson_str = run(cmd, stdout=PIPE, check=True).stdout
    geometry = json.loads(geojson_str)['features'][0]['geometry']
    return ogr.CreateGeometryFromJson(json.dumps(geometry))


def get_dem_features() -> Generator[ogr.Feature, None, None]:
    ds = ogr.Open(DEM_GEOJSON)
    layer = ds.GetLayer()
    for feature in layer:
        yield feature
    del ds


def intersects_dem(geometry: ogr.Geometry) -> bool:
    for feature in get_dem_features():
        if feature.GetGeometryRef().Intersects(geometry):
            return True
    return False


def get_dem_file_paths(geometry: ogr.Geometry) -> list[str]:
    file_paths = []
    for feature in get_dem_features():
        if feature.GetGeometryRef().Intersects(geometry):
            file_paths.append(feature.GetField('file_path'))
    return file_paths


def utm_from_lon_lat(lon: float, lat: float) -> int:
    hemisphere = 32600 if lat >= 0 else 32700
    zone = int(lon // 6 + 30) % 60 + 1
    return hemisphere + zone


def get_centroid_crossing_antimeridian(geometry: ogr.Geometry) -> ogr.Geometry:
    geojson = json.loads(geometry.ExportToJson())
    for feature in geojson['coordinates']:
        for point in feature[0]:
            if point[0] < 0:
                point[0] += 360
    shifted_geometry = ogr.CreateGeometryFromJson(json.dumps(geojson))
    return shifted_geometry.Centroid()


def shift_for_antimeridian(dem_file_paths: list[str], directory: Path) -> list[str]:
    shifted_file_paths = []
    for file_path in dem_file_paths:
        if '_W' in file_path:
            shifted_file_path = str(directory / Path(file_path).with_suffix('.vrt').name)
            corners = gdal.Info(file_path, format='json')['cornerCoordinates']
            output_bounds = [
                corners['upperLeft'][0] + 360,
                corners['upperLeft'][1],
                corners['lowerRight'][0] + 360,
                corners['lowerRight'][1],
            ]
            gdal.Translate(shifted_file_path, file_path, format='VRT', outputBounds=output_bounds)
            shifted_file_paths.append(shifted_file_path)
        else:
            shifted_file_paths.append(file_path)
    return shifted_file_paths


def convert_to_hae(dem_path: str, geoid_path: str):
    """Convert DEM to height above ellipsoid by adding geoid height.

    Args:
        dem_path: Path to an existing the DEM
        geoid_path: Path to save the geoid height GeoTIFF to
    """
    # FIXME: Doesn't supprot antimeridian crossing
    dem_ds = gdal.Open(dem_path, gdal.GA_Update)
    srs = osr.SpatialReference()
    srs.ImportFromWkt(dem_ds.GetProjection())
    epsg_code = srs.GetAuthorityCode(None)
    geotransform = dem_ds.GetGeoTransform()
    minx = geotransform[0]
    maxx = geotransform[0] + geotransform[1] * dem_ds.RasterXSize
    maxy = geotransform[3]
    miny = geotransform[3] + geotransform[5] * dem_ds.RasterYSize
    pixel_size = geotransform[1]
    gdal.Warp(
        str(geoid_path),
        GEOID,
        dstSRS=f'EPSG:{epsg_code}',
        outputBounds=[minx, miny, maxx, maxy],
        xRes=pixel_size,
        yRes=pixel_size,
        targetAlignedPixels=True,
        resampleAlg='cubic',
        multithread=True,
    )
    dem_data = dem_ds.GetRasterBand(1).ReadAsArray()
    geoid_ds = gdal.Open(str(geoid_path))
    geoid_data = geoid_ds.GetRasterBand(1).ReadAsArray()
    dem_data += geoid_data
    dem_ds.GetRasterBand(1).WriteArray(dem_data)
    dem_ds.FlushCache()
    del dem_ds, geoid_ds


def prepare_dem_geotiff(
    output_name: str,
    geometry: ogr.Geometry,
    pixel_size: float,
    epsg_code: int = None,
    height_above_ellipsoid: bool = False,
):
    """Create a DEM mosaic GeoTIFF covering a given geometry.

    The DEM mosaic is assembled from the Copernicus GLO-30 Public DEM. The output GeoTIFF covers the input geometry
    buffered by 0.15 degrees, is projected to the UTM zone of the geometry centroid, and has a pixel size of 30m.

    Args:
        output_name: Path for the output GeoTIFF
        geometry: Geometry in EPSG:4326 (lon/lat) projection for which to prepare a DEM mosaic
        pixel_size: Pixel size for the DEM in units of the DEM's projection
        epsg_code: EPSG code for the output GeoTIFF projection. If None, the UTM zone of the geometry centroid is used.
        height_above_ellipsoid: If True, the output GeoTIFF will contain height above ellipsoid values.
        format: Output GeoTIFF format
    """
    geometry = geometry.Buffer(0.15)
    minx, maxx, miny, maxy = geometry.GetEnvelope()
    if not intersects_dem(geometry):
        raise DemError(f'Copernicus GLO-30 Public DEM does not intersect this geometry: {geometry}')

    if epsg_code is None:
        centroid = geometry.Centroid()
        epsg_code = utm_from_lon_lat(centroid.GetX(), centroid.GetY())

    with GDALConfigManager(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR'):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            dem_file_paths = get_dem_file_paths(geometry)
            if geometry.GetGeometryName() == 'MULTIPOLYGON':
                centroid = get_centroid_crossing_antimeridian(geometry)
                dem_file_paths = shift_for_antimeridian(dem_file_paths, temp_path)

            dem_vrt = temp_path / 'dem.vrt'
            gdal.BuildVRT(str(dem_vrt), dem_file_paths)
            gdal.Warp(
                str(output_name),
                str(dem_vrt),
                dstSRS=f'EPSG:{epsg_code}',
                outputBounds=[minx, miny, maxx, maxy],
                xRes=pixel_size,
                yRes=pixel_size,
                targetAlignedPixels=True,
                resampleAlg='cubic',
                multithread=True,
                format='GTiff',
            )

            if height_above_ellipsoid:
                geoid_path = temp_path / 'geoid.tif'
                gdal.Warp(
                    str(geoid_path),
                    GEOID,
                    dstSRS=f'EPSG:{epsg_code}',
                    outputBounds=[minx, miny, maxx, maxy],
                    xRes=pixel_size,
                    yRes=pixel_size,
                    targetAlignedPixels=True,
                    resampleAlg='cubic',
                    multithread=True,
                )
                dem_ds = gdal.Open(output_name, gdal.GA_Update)
                dem_data = dem_ds.GetRasterBand(1).ReadAsArray()
                geoid_ds = gdal.Open(str(geoid_path))
                geoid_data = geoid_ds.GetRasterBand(1).ReadAsArray()
                dem_data += geoid_data
                dem_ds.GetRasterBand(1).WriteArray(dem_data)
                dem_ds.FlushCache()
                del dem_ds, geoid_ds
