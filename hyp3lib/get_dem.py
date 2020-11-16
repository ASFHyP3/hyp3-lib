#!/usr/bin/python3

import argparse
import logging
import math
import multiprocessing as mp
import os
import shutil
import sys
from pathlib import Path

import lxml.etree as et
import numpy as np
from osgeo import gdal
from osgeo import ogr
from osgeo import osr
from pyproj import Transformer
import configparser
from asf_geometry import raster_meta, geotiff2data, data2geotiff, geometry2shape

'''
import hyp3lib.etc
from hyp3lib import DemError
from hyp3lib import dem2isce
from hyp3lib import saa_func_lib as saa
from hyp3lib.asf_geometry import raster_meta
from hyp3lib.fetch import download_file
'''


def vector_meta(vectorFile):

    vector = ogr.Open(vectorFile)
    layer = vector.GetLayer()
    layerDefinition = layer.GetLayerDefn()
    fieldCount = layerDefinition.GetFieldCount()
    fields = []
    for ii in range(fieldCount):
        field = {}
        field['name'] = layerDefinition.GetFieldDefn(ii).GetName()
        field['type'] = layerDefinition.GetFieldDefn(ii).GetType()
        field['width'] = layerDefinition.GetFieldDefn(ii).GetWidth()
        field['precision'] = layerDefinition.GetFieldDefn(ii).GetPrecision()
        fields.append(field)
    proj = layer.GetSpatialRef()
    extent = layer.GetExtent()
    features = []
    featureCount = layer.GetFeatureCount()
    for kk in range(featureCount):
        value = {}
        feature = layer.GetFeature(kk)
        for ii in range(fieldCount):
            if fields[ii]['type'] == ogr.OFTInteger:
                value[fields[ii]['name']] = int(feature.GetField(ii))
            elif fields[ii]['type'] == ogr.OFTReal:
                value[fields[ii]['name']] = float(feature.GetField(ii))
            else:
                value[fields[ii]['name']] = feature.GetField(ii)
        value['geometry'] = feature.GetGeometryRef().ExportToWkt()
        features.append(value)

    return (fields, proj, extent, features)


def readFileList(configFile, section):

    files = []
    fileList = False
    lines = [line.rstrip('\n') for line in open(configFile)]
    for ii in range(len(lines)):
        if fileList == True:
            files.append(lines[ii])
        if section in lines[ii]:
            fileList = True

    return files


def reproject_wkt(wkt, in_epsg, out_epsg):

    source = osr.SpatialReference()
    source.ImportFromEPSG(in_epsg)

    target = osr.SpatialReference()
    target.ImportFromEPSG(out_epsg)

    transform = osr.CoordinateTransformation(source, target)

    geom = ogr.CreateGeometryFromWkt(wkt)
    geom.Transform(transform)

    return geom.ExportToWkt()


def get_dem_list(config_file):

    if config_file:
        config = configparser.ConfigParser(allow_no_value=True)
        config.optionxform = str
        config.read(config_file)

    else:
        try:
            config_file = os.path.join(str(Path.home()), '.hyp3', 'get_dem.cfg')
            config = configparser.ConfigParser(allow_no_value=True)
            config.optionxform = str
            config.read(config_file)
        except FileNotFoundError:
            config_file = os.path.join(str(Path(hyp3lib.etc.__file__).parent),
              'config', 'get_dem.cfg')
            config = configparser.ConfigParser(allow_no_value=True)
            config.optionxform = str
            config.read(config_file)

    dems = readFileList(config_file, '[Priority]')
    dem_list = []
    for name in dems:
        if config.has_section(name) == False:
            errorMessage('Config file ({0}) does not contain information ' \
                'about DEM ({1})'.format(config_file, name))
            loggingError('ERROR: ' + errorMessage)
            sys.exit(errorMessage)
        location = config[name]['path']
        shape_file = config[name]['coverage']
        if os.path.exists(shape_file) == False:
            errorMessage('Coverage shapefile ({0}) for DEM ({1}) does not ' \
                'exist!'.format(shape_file, name))
            logging.error(errorMessage)
            sys.exit(errorMessage)
        if shape_file.startswith('http'):
            shape_file = '/vsicurl/' + shape_file
        (fields, proj, extent, features) = vector_meta(shape_file)
        tile_file = os.path.join(location, features[0]['tile'] + '.tif')
        if os.path.exists(tile_file) == False:
            errorMessage('Reference DEM tile ({0}) not in path ({1})' \
                .format(tile_file, location))
            logging.error('ERROR: ' + errorMessage)
            sys.exit(errorMessage)
        (spatialRef, gt, shape, pixel) = raster_meta(tile_file)
        (data, geoTrans, proj, epsg, dtype, noData) = geotiff2data(tile_file)
        data = None
        epsg = int(proj.GetAuthorityCode(None))
        posting = gt[1]
        dem = {
            'name': name,
            'location': location,
            'epsg': epsg,
            'coverage': shape_file,
            'posting': posting,
            'geoTransform': geoTrans,
            'nodata': noData,
            'pixel': pixel
        }
        dem_list.append(dem)
    return dem_list


def change_reference(x_min, x_max, y_min, y_max, posting, inPixelRef,
    outPixelRef):

    '''
    Pixel reference 'Point' refers to the center of the pixel.
    Pixel reference 'Area' refers to the upper left corner of the pixel.
    '''
    if inPixelRef == 'Point' and outPixelRef == 'Area':
        logging.info('Shifting pixel reference from Point to Area ...')
        x_min -= 0.5 * posting
        x_max -= 0.5 * posting
        y_min += 0.5 * posting
        y_max += 0.5 * posting
    if inPixelRef == 'Area' and outPixelRef == 'Point':
        logging.info('Shifting pixel reference from Area to Point ...')
        x_min += 0.5 * posting
        x_max += 0.5 * posting
        y_min -= 0.5 * posting
        y_max -= 0.5 * posting

    return (x_min, x_max, y_min, y_max)


def get_best_dem(y_min, y_max, x_min, x_max, config_file, out_pixel,
    dem_name=None):

    dem_list = get_dem_list(config_file)
    if dem_name:
        dem_list = [dem for dem in dem_list if dem['name'] == dem_name.upper()]
        if dem_list == []:
            errorMessage = ('DEM ({0}) is not in the configuration file ' \
                '({1})'.format(dem_name, config_file))
            logging.error(errorMessage)
            sys.exit(errorMessage)

    (aoi_x_min, aoi_x_max, aoi_y_min, aoi_y_max) = (x_min, x_max, y_min, y_max)

    best_pct = 0
    bestDEM = {}
    best_tile_list = []
    best_poly_list = []
    for dem in dem_list:

        # Check pixel reference - shift if necessary
        if dem['pixel'] != out_pixel:
            (x_min, x_max, y_min, y_max) = \
                change_reference(aoi_x_min, aoi_x_max, aoi_y_min, aoi_y_max,
                                 dem['posting'], dem['pixel'], out_pixel)

        # Re-project if DEM projection is not geographic (EPSG:4326)
        aoi_wkt = ('POLYGON (({0} {2}, {1} {2}, {1} {3}, {0} {3}, {0} {2}))' \
            .format(aoi_x_min, aoi_x_max, aoi_y_min, aoi_y_max))
        if dem['epsg'] != 4326:
            logging.info("Reprojecting corners into projection EPSG:{0}" \
                .format(dem['epsg']))
            proj_wkt = reproject_wkt(aoi_wkt, 4326, dem['epsg'])
        else:
            proj_wkt = aoi_wkt
        poly = ogr.CreateGeometryFromWkt(proj_wkt)

        # Read coverage file
        (fields, proj, extent, features) = vector_meta(dem['coverage'])
        coverage = 0
        tile_list = []
        poly_list = []
        minX = x_max
        maxX = x_min
        minY = y_max
        maxY = y_min
        for feature in features:
            geometry = ogr.CreateGeometryFromWkt(feature['geometry'])
            intersection = geometry.Intersection(poly)
            area = intersection.GetArea()
            if area > 0:
                coverage += area
                tile_list.append(feature['tile'])
                poly_list.append(feature['geometry'])
                extent = \
                    ogr.CreateGeometryFromWkt(feature['geometry']).GetEnvelope()
                if extent[0] < minX:
                  minX = extent[0]
                if extent[1] > maxX:
                  maxX = extent[1]
                if extent[2] < minY:
                  minY = extent[2]
                if extent[3] > maxY:
                  maxY = extent[3]
        total_area = poly.GetArea()
        pct = coverage / total_area
        logging.info("DEM: {0}, coverage: {1}, total area: {2}, percentage {3}" \
            .format(dem['name'], coverage, total_area, pct))

        if best_pct == 0 or pct > best_pct + 0.05:
            best_pct = pct
            best_tile_list = tile_list
            best_poly_list = poly_list
            bestDEM['location'] = dem['location']
            bestDEM['name'] = dem['name']
            bestDEM['epsg'] = dem['epsg']
            bestDEM['posting'] = dem['posting']
            bestDEM['geoTransform'] = dem['geoTransform']
            bestDEM['nodata'] = dem['nodata']
            bestDEM['extent'] = (minX, maxX, minY, maxY)
            bestDEM['aoi'] = proj_wkt
        if pct >= 0.99:
            break

    if best_pct < 0.20:
        errorMessage = ('Unable to find a DEM file for that area')
        logging.error(errorMessage)
        sys.exit(errorMessage)

    logging.info('Best DEM: {0}'.format(bestDEM['name']))
    logging.info('Tile List: {0}'.format(best_tile_list))

    return bestDEM, best_tile_list, best_poly_list


def get_tile_for(args):

    dem_location, tile_name = args
    output_dir = 'DEM'
    source_file = os.path.join(dem_location, tile_name) + '.tif'
    if source_file.startswith('http'):
        download_file(source_file, directory=output_dir)
    else:
        shutil.copy(source_file, output_dir)


def write_vrt(dem_proj, nodata, tile_list, poly_list, out_file):

    # Get dimensions and pixel size from first DEM in tile ListCommand
    dem_file = os.path.join('DEM', tile_list[0] + '.tif')
    spatial_ref, gt, shape, pixel = raster_meta(dem_file)
    rows, cols = shape
    pix_x_size = gt[1]
    pix_y_size = -gt[5]

    # Determine coverage
    x_min = sys.float_info.max
    x_max = -sys.float_info.max
    y_min = sys.float_info.max
    y_max = -sys.float_info.max
    for poly in poly_list:
        polygon = ogr.CreateGeometryFromWkt(poly)
        envelope = polygon.GetEnvelope()
        if envelope[0] < x_min:
            x_min = envelope[0]
        if envelope[1] > x_max:
            x_max = envelope[1]
        if envelope[2] < y_min:
            y_min = envelope[2]
        if envelope[3] > y_max:
            y_max = envelope[3]

    raster_x_size = np.int(np.rint((x_max - x_min) / pix_x_size))
    raster_y_size = np.int(np.rint((y_max - y_min) / pix_y_size))

    # Determine offsets
    offset_x = []
    offset_y = []
    for poly in poly_list:
        polygon = ogr.CreateGeometryFromWkt(poly)
        envelope = polygon.GetEnvelope()
        offset_x.append(np.int(np.rint((envelope[0] - x_min) / pix_x_size)))
        offset_y.append(np.int(np.rint((y_max - envelope[3]) / pix_y_size)))

    # Generate XML structure
    vrt = et.Element('VRTDataset', rasterXSize=str(raster_x_size),
                     rasterYSize=str(raster_y_size))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(dem_proj)
    et.SubElement(vrt, 'SRS').text = srs.ExportToWkt()
    geo_trans = ('%.16f, %.16f, 0.0, %.16f, 0.0, %.16f' % (x_min, pix_x_size,
        y_max, -pix_y_size))
    et.SubElement(vrt, 'GeoTransform').text = geo_trans
    bands = et.SubElement(vrt, 'VRTRasterBand', dataType='Float32', band='1')
    et.SubElement(bands, 'NoDataValue').text = str(nodata)
    et.SubElement(bands, 'ColorInterp').text = 'Gray'
    tile_count = len(tile_list)
    for ii in range(tile_count):
        source = et.SubElement(bands, 'ComplexSource')
        dem_file = tile_list[ii] + '.tif'
        spatial_ref, gt, shape, pixel = \
            raster_meta(os.path.join('DEM', dem_file))
        rows, cols = shape
        et.SubElement(source, 'SourceFilename', relativeToVRT='1').text = \
            dem_file
        et.SubElement(source, 'SourceBand').text = '1'
        properties = et.SubElement(source, 'SourceProperties')
        properties.set('RasterXSize', str(cols))
        properties.set('RasterYSize', str(rows))
        properties.set('DataType', 'Float32')
        properties.set('BlockXSize', str(cols))
        properties.set('BlockYSize', '1')
        src = et.SubElement(source, 'SrcRect')
        src.set('xOff', '0')
        src.set('yOff', '0')
        src.set('xSize', str(cols))
        src.set('ySize', str(rows))
        dst = et.SubElement(source, 'DstRect')
        dst.set('xOff', str(offset_x[ii]))
        dst.set('yOff', str(offset_y[ii]))
        dst.set('xSize', str(cols))
        dst.set('ySize', str(rows))
        et.SubElement(source, 'NODATA').text = str(nodata)

    # Write VRT file
    with open(out_file, 'wb') as outF:
        outF.write(et.tostring(vrt, xml_declaration=False, encoding='utf-8',
                               pretty_print=True))


def scale_posting(bestDEM, posting, out_proj):

    res = -1
    scale = 30.0 / 0.000277778

    # unit: degrees
    if out_proj == 'dem':
        pass
    elif bestDEM['epsg'] == 4326 or bestDEM['epsg'] == 4269:
        if out_proj == 'utm' or out_proj == 'polar':
            demPosting = bestDEM['posting'] * scale

        if (demPosting / posting) > 2.0:
            scale_factor = demPosting / posting / 2.0
            res = int(demPosting / scale_factor / posting * 100)
        elif (posting / demPosting) > 2.0:
            scale_factor = posting / demPosting / 2.0
            res = int(demPosting * scale_factor / posting * 100)


    # unit: meters
    else:
        if out_proj == 'latlon':
            demPosting = bestDEM['posting'] / scale
        else:
            demPosting = bestDEM['posting']

        if (demPosting / posting) > 2.0:
            scale_factor = demPosting / posting / 2.0
            res = int(demPosting / scale_factor / posting * 100)
        elif (posting / demPosting) > 2.0:
            scale_factor = posting / demPosting / 2.0
            res = int(demPosting * scale_factor / posting * 100)

    if res > 0:
        logging.info('DEM resampling posting: {0}%'.format(res))

    return res


def get_dem(x_min, y_min, x_max, y_max, outfile, posting=0.0, processes=4,
    dem_name=None, leave=False, config_file=None, snap_to_grid=False,
    pixel_reference='Point', out_proj='utm', out_format='GeoTIFF'):

    # Check input
    if y_min < -90 or y_max > 90:
        errorMessage = 'Latitude outside valid range (-90, 90) ({0}, {1})' \
            .format(y_min, y_max)
        logging.error(errorMessage)
        sys.exit(errorMessage)
    if x_min > x_max:
        logging.warning("WARNING: minimum longitude > maximum longitude - swapping")
        (x_min, x_max) = (x_max, x_min)

    if y_min > y_max:
        logging.warning("WARNING: minimum latitude > maximum latitude - swapping")
        (y_min, y_max) = (y_max, y_min)

    if out_proj not in ['dem', 'utm', 'polar', 'latlon']:
        errorMessage = ("Unknown output map projection ('{0}')! Needs to be " \
            "either 'dem', 'utm', 'polar', 'latlon'.".format(out_proj))
        logging.error(errorMessage)
        sys.exit(errorMessage)
    if pixel_reference not in ['Point', 'Area']:
        errorMessage = ("Unkwown pixel reference ('{0}')! Needs to be either " \
            "'Point' or 'Area'.".format(pixel_reference))
        logging.error(errorMessage)
        sys.exit(errorMessage)
    if out_format not in ['GeoTIFF', 'ISCE']:
        errorMessage = ("Unknown output format ('{0}')! Needs to be either " \
            "'GeoTIFF' or 'ISCE'.".format(out_format))
        logging.error(errorMessage)
        sys.exit(errorMessage)

    if config_file:
        if os.path.exists(config_file) == False:
            errorMessage = ('Config file ({0}) does not exist!' \
                .format(config_file))
            logging.error(errorMessage)
            sys.exit(errorMessage)

    if posting > 0.01 and out_proj == 'latlon':
        errorMessage = ('Posting ({0}) too big for geographic coordinates.' \
            .format(posting))
        logging.error(errorMessage)
        sys.exit(errorMessage)
    elif posting < 1.0 and out_proj != 'latlon':
        errorMessage = ('Posting ({0}) too small for non-geographic ' \
            'coordinates.'.format(posting))
        logging.error(errorMessage)
        sys.exit(errorMessage)

    # Figure out which DEM and get the tile list
    (bestDEM, tile_list, poly_list) = \
        get_best_dem(y_min, y_max, x_min, x_max, config_file, pixel_reference,
            dem_name=dem_name)
    logging.info("DEM EPSG code: {0}".format(bestDEM['epsg']))

    # Copy the files into a DEM directory
    if not os.path.isdir("DEM"):
        os.mkdir("DEM")

    # Download tiles in parallel
    logging.info("Fetching DEM tiles to local storage ...")
    p = mp.Pool(processes=processes)
    p.map(
        get_tile_for,
        [(bestDEM['location'], fi) for fi in tile_list]
    )
    p.close()
    p.join()

    # Generate local DEM mosaic
    VRT = os.path.join('DEM', 'temp.vrt')
    write_vrt(bestDEM['epsg'], bestDEM['nodata'], tile_list, poly_list, VRT)

    # Calculate geographic centroid for AOI
    aoiPolygon = ogr.CreateGeometryFromWkt(bestDEM['aoi'])
    aoiCenter = aoiPolygon.Centroid()
    centerWkt = reproject_wkt(aoiCenter.ExportToWkt(), bestDEM['epsg'], 4326)
    aoiCenter = ogr.CreateGeometryFromWkt(centerWkt)
    centerLat = aoiCenter.GetY()
    centerLon = aoiCenter.GetX()

    # Save AOI polygon shapefile
    multiPolygon = ogr.Geometry(ogr.wkbMultiPolygon)
    multiPolygon.AddGeometry(aoiPolygon)
    fields = []
    field = {}
    field['name'] = 'aoi'
    field['type'] = ogr.OFTInteger
    fields.append(field)
    values = []
    value = {}
    value['aoi'] = 1
    value['geometry'] = multiPolygon
    values.append(value)
    proj = osr.SpatialReference()
    proj.ImportFromEPSG(bestDEM['epsg'])
    aoiShapefile = os.path.join('DEM', 'aoi.shp')
    geometry2shape(fields, values, proj, False, aoiShapefile)

    # Set mapping parameters
    srcSRS = ('EPSG:{0}'.format(bestDEM['epsg']))
    if out_proj == 'dem':
        dstSRS = srcSRS
    elif out_proj == 'latlon':
        dstSRS = 'EPSG:4326'
    elif out_proj == 'polar':
        if centerLat > 0:
            dstSRS = 'EPSG:3413'
        else:
            dstSRS = 'EPSG:3031'
    else:
        zone = math.floor((centerLon + 180) / 6 + 1)
        if zone > 60:
            zone -= 60
        if centerLat > 0:
            dstSRS = ('EPSG:326%02d' % int(zone))
        else:
            dstSRS = ('EPSG:327%02d' % int(zone))
    scaleOnly = False
    if srcSRS == dstSRS or (srcSRS == 4269 and dstSRS == 4326):
        scaleOnly = True

    # Set output format
    if out_format == 'GeoTIFF':
        outFormat = 'GTiff'
    elif out_format == 'ISCE':
        outFormat = 'ISCE'
    else:
        logging.error("Unknown output format ('{0}')! Needs to be either " \
            "'GeoTIFF' or 'ISCE'.".format(args.format))
        sys.exit(1)

    # Mapping DEM mosaic into output space
    mapped_file = os.path.join('DEM', 'mapped.tif')
    if scaleOnly == False:
        scaled_file = os.path.join('DEM', 'scaled.tif')
        scale = scale_posting(bestDEM, posting, out_proj)
        if scale > 0:
            logging.info('Resampling DEM ...')
            gdal.Translate(scaled_file, VRT, heightPct=scale, widthPct=scale,
                format='GTiff')
        logging.info("Mapping DEM mosaic into output space ...")
        gdal.Warp(mapped_file, scaled_file, xRes=posting, yRes=posting,
            srcNodata=bestDEM['nodata'], srcSRS=srcSRS, dstSRS=dstSRS,
            resampleAlg='cubic', cropToCutline=True, cutlineDSName=aoiShapefile,
            targetAlignedPixels=snap_to_grid, format=outFormat)
    else:
        if scaleOnly == True:
            logging.info('Resampling DEM ...')
        else:
            logging.info("Mapping DEM mosaic into output space ...")
        gdal.Warp(mapped_file, VRT, xRes=posting, yRes=posting,
            srcNodata=bestDEM['nodata'], srcSRS=srcSRS, dstSRS=dstSRS,
            resampleAlg='cubic', cropToCutline=True, cutlineDSName=aoiShapefile,
            targetAlignedPixels=snap_to_grid, format=outFormat)

    # Cleaning up no data value
    logging.info("Setting no data value to -32767 ...")
    (data, geoTrans, proj, epsg, dtype, noData) = geotiff2data(mapped_file)
    data[data <= -1000] = -32767
    data2geotiff(data, geoTrans, proj, dtype, -32767, outfile)

    # Clean up intermediate files
    if leave == True:
        logging.info("Keeping intermediate files ...")
    else:
        logging.info("Removing intermediate files ...")
        shutil.rmtree('DEM')


def positive_int(value):
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError("{value} is an invalid positive int value")
    return ivalue


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument("x_min", help="minimum longitude", type=float)
    parser.add_argument("y_min", help="minimum latitude", type=float)
    parser.add_argument("x_max", help="maximum longitude", type=float)
    parser.add_argument("y_max", help="maximum latitude", type=float)
    parser.add_argument("outfile", help="output DEM name")
    parser.add_argument("posting", type=float, help="Posting of the output DEM")
    parser.add_argument("-d", "--dem", help="Type of DEM to use")
    parser.add_argument("-t", "--threads", type=positive_int, default=1,
                        help="Number of threads to use for downloading DEM tiles")
    parser.add_argument("-c", "--config", default=None,
                        help="Parsing in DEM config file manually")
    parser.add_argument("-r", "--reference",
                        help="Pixel reference: Point or Area", default="Point")
    parser.add_argument("-o", "--output",
                        help="Output map projection: dem, utm, polar, latlon",
                        default="utm")
    parser.add_argument("-f", "--format", help="Output format: GeoTIFF or ISCE",
                        default="GeoTIFF")
    parser.add_argument("-g", "--grid", action='store_true', default=False,
                        help="Snapping to grid")
    parser.add_argument("-k", "--keep", action='store_true', default=False,
                        help="Keep intermediate DEM results")
    args = parser.parse_args()

    log_file = ("get_dem_{0}.log".format(os.getpid()))
    logging.basicConfig(filename=log_file,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.info("Starting run")

    get_dem(
        args.x_min, args.y_min, args.x_max, args.y_max, args.outfile,
        posting=args.posting, leave=args.keep, processes=args.threads,
        dem_name=args.dem, config_file=args.config,
        snap_to_grid=args.grid, pixel_reference=args.reference,
        out_proj=args.output, out_format=args.format
    )


if __name__ == "__main__":
    main()
