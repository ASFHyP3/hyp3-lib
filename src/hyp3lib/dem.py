from collections.abc import Generator
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

from osgeo import gdal, ogr

from hyp3lib import DemError
from hyp3lib.util import GDALConfigManager


DEM_GEOJSON = '/vsicurl/https://asf-dem-west.s3.amazonaws.com/v2/cop30_20250404.geojson'
GEOID = '/vsicurl/https://asf-dem-west.s3.amazonaws.com/GEOID/us_nga_egm2008_1.tif'

gdal.UseExceptions()
ogr.UseExceptions()


def _get_dem_features() -> Generator[ogr.Feature, None, None]:
    ds = ogr.Open(DEM_GEOJSON)
    layer = ds.GetLayer()
    for feature in layer:
        yield feature
    del ds


def _intersects_dem(geometry: ogr.Geometry) -> bool:
    for feature in _get_dem_features():
        if feature.GetGeometryRef().Intersects(geometry):
            return True
    return False


def _get_dem_file_paths(geometry: ogr.Geometry) -> list[str]:
    file_paths = []
    for feature in _get_dem_features():
        if feature.GetGeometryRef().Intersects(geometry):
            file_paths.append(feature.GetField('file_path'))
    return file_paths


def _convert_to_height_above_ellipsoid(dem_file: Path) -> None:
    dem_info = gdal.Info(str(dem_file), format='json')
    minx = dem_info['cornerCoordinates']['lowerLeft'][0]
    miny = dem_info['cornerCoordinates']['lowerLeft'][1]
    maxx = dem_info['cornerCoordinates']['upperRight'][0]
    maxy = dem_info['cornerCoordinates']['upperRight'][1]
    with NamedTemporaryFile() as geoid_file:
        gdal.Warp(
            geoid_file.name,
            GEOID,
            dstSRS=dem_info['coordinateSystem']['wkt'],
            outputBounds=[minx, miny, maxx, maxy],
            width=dem_info['size'][0],
            height=dem_info['size'][1],
            resampleAlg='cubic',
            multithread=True,
            format='GTiff',
        )
        geoid_ds = gdal.Open(geoid_file.name)
        geoid_data = geoid_ds.GetRasterBand(1).ReadAsArray()
        del geoid_ds

        dem_ds = gdal.Open(str(dem_file), gdal.GA_Update)
        dem_data = dem_ds.GetRasterBand(1).ReadAsArray()
        dem_data += geoid_data
        dem_ds.GetRasterBand(1).WriteArray(dem_data)
        dem_ds.FlushCache()
        del dem_ds


def prepare_dem_geotiff(
    output_name: Path,
    geometry: ogr.Geometry,
    epsg_code: int,
    pixel_size: float,
    buffer_size_in_degrees: float = 0.0,
    height_above_ellipsoid: bool = False,
) -> Path:
    """Create a DEM mosaic GeoTIFF covering a given geometry.

    The DEM mosaic is assembled from the Copernicus GLO-30 Public DEM and reprojected into the given EPSG code and pixel
    size. The extent of the output GeoTIFF is the extent of the buffered input geometry.

    Args:
        output_name: Path for the output GeoTIFF
        geometry: Geometry in EPSG:4326 (lon/lat) projection for which to prepare a DEM mosaic. Must be a POLYGON with
          longitude coordinates between -180 and +200 degrees.
        epsg_code: EPSG code for the output GeoTIFF projection.
        pixel_size: Pixel size for the DEM in units of the DEM's projection
        buffer_size_in_degrees: Extent of the output geotiff will be the extent of the buffered input geometry.
        height_above_ellipsoid:
          If False, output pixel values will be meters above mean sea level.
          If True, the output pixel values will be meters above the ellipsoid.
          Only supported for geometries between -180 and +180 degrees longitude (i.e. geometries not crossing the antimeridian).
    """
    if geometry.GetGeometryName() != 'POLYGON':
        raise DemError(f'{geometry.GetGeometryName()} geometry is invalid; only POLYGON is supported.')

    if not _intersects_dem(geometry):
        raise DemError(f'Copernicus GLO-30 Public DEM does not intersect this geometry: {geometry}')

    buffered_geometry = geometry.Buffer(buffer_size_in_degrees)
    minx, maxx, miny, maxy = buffered_geometry.GetEnvelope()
    if not (-180 <= minx <= maxx <= 200):
        raise DemError(f'Extent of buffered geometry ({minx} - {maxx}) is not between -180 and +200 degrees longitude.')

    if 180 < maxx and height_above_ellipsoid:
        raise DemError('height_above_ellipsoid is not supported for geometries with coordinates between +180 and +200 degrees longitude.')

    with GDALConfigManager(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR'):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            dem_file_paths = _get_dem_file_paths(buffered_geometry)

            dem_vrt = temp_path / 'dem.vrt'
            gdal.BuildVRT(str(dem_vrt), dem_file_paths)
            # This is required to ensure the VRT is treated as a point dataset
            vrt_ds = gdal.Open(str(dem_vrt), gdal.GA_Update)
            vrt_ds.SetMetadataItem('AREA_OR_POINT', 'Point')
            vrt_ds = None
            gdal.Warp(
                str(output_name),
                str(dem_vrt),
                dstSRS=f'EPSG:{epsg_code}',
                outputBoundsSRS='EPSG:4326',
                outputBounds=[minx, miny, maxx, maxy],
                xRes=pixel_size,
                yRes=pixel_size,
                targetAlignedPixels=True,
                resampleAlg='cubic',
                multithread=True,
                format='GTiff',
            )

    if height_above_ellipsoid:
        _convert_to_height_above_ellipsoid(output_name)

    return output_name
