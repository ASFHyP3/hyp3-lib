"""Get a DEM file in .tif format from the ASF DEM heap"""

import argparse
import logging
import math
import multiprocessing as mp
import os
import shutil
import subprocess
import sys

import boto3
import lxml.etree as et
import numpy as np
from botocore.handlers import disable_signing
from osgeo import gdal
from osgeo import ogr
from osgeo import osr
from pyproj import Transformer

import hyp3lib.etc
from hyp3lib import DemError
from hyp3lib import dem2isce
from hyp3lib import saa_func_lib as saa
from hyp3lib.asf_geometry import raster_meta


def reproject_wkt(wkt, in_epsg, out_epsg):
    source = osr.SpatialReference()
    source.ImportFromEPSG(in_epsg)

    target = osr.SpatialReference()
    target.ImportFromEPSG(out_epsg)

    transform = osr.CoordinateTransformation(source, target)

    geom = ogr.CreateGeometryFromWkt(wkt)
    geom.Transform(transform)

    return geom.ExportToWkt()


def get_dem_list():
    config_dir = os.path.abspath(os.path.join(os.path.dirname(hyp3lib.etc.__file__), "config"))
    config_file = os.path.join(config_dir, "get_dem.py.cfg")
    with open(config_file) as f:
        dem_list = [
            {
                'name': line.split()[0],
                'epsg': int(line.split()[2])
            }
            for line in f.readlines()
        ]
    return dem_list


def get_best_dem(y_min, y_max, x_min, x_max, dem_name=None):
    dem_list = get_dem_list()
    if dem_name:
        dem_list = [dem for dem in dem_list if dem['name'] == dem_name]

    scene_wkt = f"POLYGON (({x_min} {y_min}, {x_max} {y_min}, {x_max} {y_max}, {x_min} {y_max}, {x_min} {y_min}))"

    best_pct = 0
    best_name = ""
    best_epsg = ""
    best_tile_list = []
    best_poly_list = []

    for dem in dem_list:
        if dem['epsg'] != 4326:
            logging.info(f"Reprojecting corners into projection {dem['epsg']}")
            proj_wkt = reproject_wkt(scene_wkt, 4326, dem['epsg'])
        else:
            proj_wkt = scene_wkt

        driver = ogr.GetDriverByName('ESRI Shapefile')
        shpdir = os.path.abspath(os.path.join(os.path.dirname(hyp3lib.etc.__file__), "config"))
        dataset = driver.Open(os.path.join(shpdir, dem['name'].lower() + '_coverage.shp'), 0)
        poly = ogr.CreateGeometryFromWkt(proj_wkt)
        total_area = poly.GetArea()
        coverage = 0
        tiles = ""
        tile_list = []
        poly_list = []
        layer = dataset.GetLayer()
        for i in range(layer.GetFeatureCount()):
            feature = layer.GetFeature(i)
            wkt = feature.GetGeometryRef().ExportToWkt()

            tile_poly = ogr.CreateGeometryFromWkt(wkt)
            intersect = tile_poly.Intersection(poly)
            a = intersect.GetArea()
            if a > 0:
                poly_list.append(wkt)
                tile = str(feature.GetFieldAsString(feature.GetFieldIndex("tile")))
                coverage += a
                tiles += "," + tile
                tile_list.append(tile)

        pct = coverage / total_area
        logging.info(f"Totals: {dem} {coverage} {total_area} {pct}")

        if best_pct == 0 or pct > best_pct + 0.05:
            best_pct = pct
            best_name = dem['name']
            best_tile_list = tile_list
            best_epsg = dem['epsg']
            best_poly_list = poly_list
        if pct >= .99:
            break

    if best_pct < .20:
        raise DemError("Unable to find a DEM file for that area")

    logging.info(f"Best DEM: {best_name}")
    logging.info(f"Tile List: {best_tile_list}")
    return best_name, best_epsg, best_tile_list, best_poly_list


def get_tile_for(args):
    demname, fi = args
    cfgdir = os.path.abspath(os.path.join(os.path.dirname(hyp3lib.etc.__file__), "config"))
    myfile = os.path.join(cfgdir, "get_dem.py.cfg")

    with open(myfile) as f:
        content = f.readlines()
        for item in content:
            if demname in item.split()[0] and len(demname) == len(item.split()[0]):
                (mydir, myfile) = os.path.split(item)
                mydir = mydir.split()[1]
                if "s3" in mydir:
                    myfile = os.path.join(demname, fi) + ".tif"
                    s3 = boto3.resource('s3')
                    s3.meta.client.meta.events.register('choose-signer.s3.*', disable_signing)
                    mybucket = mydir.split("/")[-1]
                    s3.Bucket(mybucket).download_file(myfile, f"DEM/{fi}.tif")
                else:
                    myfile = os.path.join(mydir, demname, "geotiff", fi) + ".tif"
                    output = f"DEM/{fi}].tif"
                    shutil.copy(myfile, output)


def _parse_gdal_coordinate_line(line):
    """returns (394560.0, 5922090.0) from a line like:
        Upper Left  (  394560.000, 5922090.000) (  1d24'45.77"E, 53d26'14.23"N)
    """
    east, north = line.split('(')[1].strip().rstrip(')').split(',')
    return float(east), float(north)


def get_corner_coordinates_from_gdal_info(info):
    coords = {}
    keys = ['Upper Left', 'Lower Left', 'Upper Right', 'Lower Right']
    for line in info.split('\n'):
        for key in keys:
            if key in line:
                coords[key] = _parse_gdal_coordinate_line(line)
    return coords


def get_cc(tmpproj, post):
    shift = 0
    info = subprocess.check_output(f'gdalinfo {tmpproj}', shell=True, universal_newlines=True)
    coords = get_corner_coordinates_from_gdal_info(info)

    easts = [c[0] for c in coords.values()]
    norths = [c[1] for c in coords.values()]

    e_max = math.ceil(max(easts) / post) * post + shift
    e_min = math.floor(min(easts) / post) * post - shift
    n_max = math.ceil(max(norths) / post) * post + shift
    n_min = math.floor(min(norths) / post) * post - shift

    logging.info("New coordinates: %f %f %f %f" % (e_max, e_min, n_max, n_min))
    return e_min, e_max, n_min, n_max


def write_vrt(dem_proj, nodata, tile_list, poly_list, out_file):
    # Get dimensions and pixel size from first DEM in tile ListCommand
    dem_file = os.path.join('DEM', f'{tile_list[0]}.tif')
    spatial_ref, gt, shape, pixel = raster_meta(dem_file)
    rows, cols = shape
    pix_size = gt[1]

    # Determine coverage
    min_lon = 360
    max_lon = -180
    min_lat = 90
    max_lat = -90
    for poly in poly_list:
        polygon = ogr.CreateGeometryFromWkt(poly)
        envelope = polygon.GetEnvelope()
        if envelope[0] < min_lon:
            min_lon = envelope[0]
        if envelope[1] > max_lon:
            max_lon = envelope[1]
        if envelope[2] < min_lat:
            min_lat = envelope[2]
        if envelope[3] > max_lat:
            max_lat = envelope[3]

    raster_x_size = np.int(np.rint((max_lon - min_lon) / pix_size)) + 1
    raster_y_size = np.int(np.rint((max_lat - min_lat) / pix_size)) + 1

    # Determine offsets
    offset_x = []
    offset_y = []
    for poly in poly_list:
        polygon = ogr.CreateGeometryFromWkt(poly)
        envelope = polygon.GetEnvelope()
        offset_x.append(np.int(np.rint((envelope[0] - min_lon) / pix_size)))
        offset_y.append(np.int(np.rint((max_lat - envelope[3]) / pix_size)))

    # Generate XML structure
    vrt = et.Element('VRTDataset', rasterXSize=str(raster_x_size),
                     rasterYSize=str(raster_y_size))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(dem_proj)
    et.SubElement(vrt, 'SRS').text = srs.ExportToWkt()
    geo_trans = f'{min_lon:.16f}, {pix_size:.16f}, 0.0, {max_lat:.16f}, 0.0, {-pix_size:.16f}'
    et.SubElement(vrt, 'GeoTransform').text = geo_trans
    bands = et.SubElement(vrt, 'VRTRasterBand', dataType='Float32', band='1')
    et.SubElement(bands, 'NoDataValue').text = '-32768'
    et.SubElement(bands, 'ColorInterp').text = 'Gray'
    tile_count = len(tile_list)
    for ii in range(tile_count):
        source = et.SubElement(bands, 'ComplexSource')
        dem_file = os.path.join('DEM', f'{tile_list[ii]}.tif')
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
        et.SubElement(source, 'NODATA').text = f"{nodata}"

    # Write VRT file
    with open(out_file, 'wb') as outF:
        outF.write(et.tostring(vrt, xml_declaration=False, encoding='utf-8',
                               pretty_print=True))


def get_dem(x_min, y_min, x_max, y_max, outfile, post=None, processes=1, dem_name=None, leave=False, dem_type='utm'):
    if post is not None:
        logging.info(f"Snapping to grid at posting of {post} meters")

    if y_min < -90 or y_max > 90:
        raise ValueError(f"Please use latitude in range (-90, 90) ({y_min}, {y_max})")

    if x_min > x_max:
        logging.warning("WARNING: minimum easting > maximum easting - swapping")
        (x_min, x_max) = (x_max, x_min)

    if y_min > y_max:
        logging.warning("WARNING: minimum northing > maximum northing - swapping")
        (y_min, y_max) = (y_max, y_min)

    # Figure out which DEM and get the tile list
    (demname, demproj, tile_list, poly_list) = get_best_dem(y_min, y_max, x_min, x_max, dem_name=dem_name)
    demproj = int(demproj)
    logging.info(f"demproj is {demproj}")

    # Add buffer for REMA
    if 'REMA' in demname or 'GIMP' in demname:
        x_min -= 4
        x_max += 4
    if 'EU_DEM' in demname:
        y_min -= 2
        y_max += 2

    # Copy the files into a dem directory
    if not os.path.isdir("DEM"):
        os.mkdir("DEM")

    # Download tiles in parallel
    logging.info("Fetching DEM tiles to local storage")
    p = mp.Pool(processes=processes)
    p.map(
        get_tile_for,
        [(demname, fi) for fi in tile_list]
    )
    p.close()
    p.join()

    # os.system("gdalbuildvrt temp.vrt DEM/*.tif")
    if "SRTMGL" in demname:
        nodata = -32768
    elif "GIMP" in demname:
        nodata = None
    elif "REMA" in demname:
        nodata = 0
    elif "NED" in demname or "EU_DEM_V11" in demname:
        nodata = -3.4028234663852886e+38
    else:
        raise DemError(f'Unable to determine NoData value for DEM {demname}')

    write_vrt(demproj, nodata, tile_list, poly_list, 'temp.vrt')

    #
    # Set the output projection to either NPS, SPS, or UTM
    #
    if demproj == 3413:  # North Polar Stereo
        outproj = 'EPSG:3413'
        outproj_num = 3413
    elif demproj == 3031:  # South Polar Stereo
        outproj = 'EPSG:3031'
        outproj_num = 3031
    else:
        lon = (x_max + x_min) / 2
        zone = math.floor((lon + 180) / 6 + 1)
        if zone > 60:
            zone -= 60
        if (y_min + y_max) / 2 > 0:
            outproj = ('EPSG:326%02d' % int(zone))
            outproj_num = int("326%02d" % int(zone))
        else:
            outproj = ('EPSG:327%02d' % int(zone))
            outproj_num = int("327%02d" % int(zone))

    tmpdem = "xxyyzz_img.tif"
    tmpdem2 = "aabbcc_img.tif"
    tmpproj = "lmnopqr_img.tif"
    if os.path.isfile(tmpdem):
        logging.info(f"Removing old file {tmpdem}")
        os.remove(tmpdem)
    if os.path.isfile(tmpproj):
        logging.info("Removing old file projected dem file")
        os.remove(tmpproj)

    pixsize = 30.0
    gcssize = 0.00027777777778

    if demname == "SRTMGL3":
        pixsize = 90.
        gcssize *= 3
    if demname == "NED2":
        pixsize = 60.
        gcssize *= 2

    logging.info("Creating initial raster file")
    logging.info(f"    tmpdem {tmpdem}")
    logging.info(f"    pixsize {pixsize}")
    logging.info(f"    bounds: x_min {x_min}; y_min {y_min}; x_max {x_max}; y_max {y_max}")

    # xform bounds to projection of the DEM
    if demproj != 4326:
        transformer = Transformer.from_crs('epsg:4326', f'epsg:{demproj}')
        t_x, t_y = transformer.transform([x_min, x_max], [y_min, y_max])
        x_min, x_max = sorted(t_x)
        y_min, y_max = sorted(t_y)
        logging.info(f"    transformed bounds: x_min {x_min}; y_min {y_min}; x_max {x_max}; y_max {y_max}")

    if demproj == 4269 or demproj == 4326:
        res = gcssize
    else:
        res = pixsize
    gdal.Warp(tmpdem, "temp.vrt", xRes=res, yRes=res, outputBounds=[x_min, y_min, x_max, y_max],
              resampleAlg="cubic", dstNodata=-32767)

    # If DEM is from NED collection, then it will have a NAD83 ellipse -
    # need to convert to WGS84
    # Also, need to convert from pixel as area to pixel as point
    if "NED" in demname:
        logging.info("Converting to WGS84")
        gdal.Warp("temp_dem_wgs84.tif", tmpdem, dstSRS="EPSG:4326")
        logging.info("Converting to pixel as point")
        x1, y1, t1, p1, data = \
            saa.read_gdal_file(saa.open_gdal_file("temp_dem_wgs84.tif"))
        lon = t1[0]
        resx = t1[1]
        rotx = t1[2]
        lat = t1[3]
        roty = t1[4]
        resy = t1[5]
        lon = lon + resx / 2.0
        lat = lat + resy / 2.0
        t1 = [lon, resx, rotx, lat, roty, resy]
        saa.write_gdal_file_float(tmpdem, t1, p1, data)
        if not leave:
            os.remove("temp_dem_wgs84.tif")

    clean_dem(tmpdem, tmpdem2)
    shutil.move(tmpdem2, tmpdem)
    gdal.Translate(tmpdem2, tmpdem, metadataOptions=['AREA_OR_POINT=Point'])
    shutil.move(tmpdem2, tmpdem)

    # Reproject the DEM file into UTM space
    if demproj != outproj_num:
        logging.info(f"Translating raster file to projected coordinates ({outproj})")
        gdal.Warp(tmpproj, tmpdem, dstSRS=outproj, xRes=pixsize, yRes=pixsize, resampleAlg="cubic",
                  srcNodata=-32767, dstNodata=-32767)
        infile = tmpproj
    else:
        infile = tmpdem

    report_min(infile)

    # Snap to posting grid
    if post:
        snap_to_grid(post, pixsize, infile, outfile)
    else:
        shutil.copy(infile, outfile)

    report_min(outfile)

    # Clean up intermediate files
    if not leave:
        if os.path.isfile(tmpdem):
            logging.info(f"Removing temp file {tmpdem}")
            os.remove(tmpdem)
        if os.path.isfile(tmpproj):
            logging.info(f"Removing temp file {tmpproj}")
            os.remove(tmpproj)

    logging.info("Successful Completion!")
    if dem_type.lower() == 'utm':
        return demname

    elif dem_type.lower() == 'latlon':
        pixsize = 0.000277777777778
        gdal.Warp(
            "temp_dem.tif", outfile, dstSRS="EPSG:4326", xRes=pixsize, yRes=pixsize, resampleAlg="cubic",
            dstNodata=-32767
        )
        shutil.move("temp_dem.tif", outfile)

    elif dem_type.lower() == 'isce':
        pixsize = 0.000277777777778
        gdal.Warp("temp_dem.tif", outfile, format="ENVI", dstSRS="EPSG:4326", xRes=pixsize, yRes=pixsize,
                  resampleAlg="cubic", dstNodata=-32767)
        shutil.move("temp_dem.tif", outfile)
        hdr_name = os.path.splitext(outfile)[0] + ".hdr"
        dem2isce.dem2isce(outfile, hdr_name, f'{outfile}.xml')

    else:
        raise NotImplementedError(f'Cannot get DEM for unkown type {dem_type}')

    return demname


def report_min(in_dem):
    (x, y, trans, proj, data) = saa.read_gdal_file(saa.open_gdal_file(in_dem))
    logging.debug(f"DEM file {in_dem} minimum is {np.min(data)}")


def clean_dem(in_dem, out_dem):
    (x, y, trans, proj, data) = saa.read_gdal_file(saa.open_gdal_file(in_dem))
    logging.info("Replacing values less than -1000 with zero")
    data[data <= -1000] = -32767
    logging.info(f"DEM Maximum value: {np.max(data)}")
    logging.info(f"DEM minimum value: {np.min(data)}")

    if data.dtype == np.float32:
        saa.write_gdal_file_float(out_dem, trans, proj, data.astype(np.float32))
    elif data.dtype == np.uint16:
        saa.write_gdal_file(out_dem, trans, proj, data)
    else:
        logging.error(f"ERROR: Unknown DEM data type {data.dtype}")
        sys.exit(1)


def snap_to_grid(post, pixsize, infile, outfile):
    if post:
        logging.info(f"Snapping file to grid at {post} meters")
        (e_min, e_max, n_min, n_max) = get_cc(infile, post)
        bounds = [e_min, n_min, e_max, n_max]
        gdal.Warp(outfile, infile, xRes=pixsize, yRes=pixsize, outputBounds=bounds, resampleAlg="cubic",
                  dstNodata=-32767)
    else:
        logging.info("Copying DEM to output file name")
        shutil.copy(infile, outfile)


def positive_int(value):
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f"{value} is an invalid positive int value")
    return ivalue


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument("x_min", help="minimum longitude/easting", type=float)
    parser.add_argument("y_min", help="minimum latitude/northing", type=float)
    parser.add_argument("x_max", help="maximum longitude/easting", type=float)
    parser.add_argument("y_max", help="maximum latitude/northing", type=float)
    parser.add_argument("outfile", help="output DEM name")
    parser.add_argument("-p", "--posting", type=float, help="Snap DEM to align with grid at given posting")
    parser.add_argument("-d", "--dem", help="Type of DEM to use")
    parser.add_argument("-t", "--threads", type=positive_int, default=1,
                        help="Num of threads to use for downloading DEM tiles")
    parser.add_argument("-l", "--latlon", action='store_true',
                        help="Create output in GCS coordinates (default is native DEM projection)")
    parser.add_argument("-k", "--keep", action='store_true', help="Keep intermediate DEM results")
    args = parser.parse_args()

    log_file = f"get_dem_{os.getpid()}.log"
    logging.basicConfig(filename=log_file, format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.info("Starting run")

    if args.latlon:
        dem_type = 'latlon'
    else:
        dem_type = 'utm'

    get_dem(
        args.x_min, args.y_min, args.x_max, args.y_max, args.outfile,
        post=args.posting, leave=args.keep, processes=args.threads, dem_name=args.dem, dem_type=dem_type
    )


if __name__ == "__main__":
    main()
