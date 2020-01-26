#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
###############################################################################
# get_dem.py
#
# Project:  APD general tool
# Purpose:  Get a DEM for a given bounding box
#
# Author:   Kirk Hogenson, Tom Logan
#
###############################################################################
# Copyright (c) 2017, Alaska Satellite Facility
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
###############################################################################
import ogr
import os
import sys
import shutil
import math
from osgeo import gdal, ogr, osr
import argparse
import boto3
from botocore.handlers import disable_signing
import subprocess
import dem2isce
import saa_func_lib as saa
import multiprocessing as mp
import lxml.etree as et
import numpy as np
from asf_geometry import raster_meta
import logging
from osgeo import ogr
from osgeo import osr
from pyproj import Proj, transform

def transform_bounds(inb, inepsg, outepsg):
    ptx = inb[0]
    pty = inb[1]
    ret1 = transform_point(ptx,pty,inepsg,outepsg)
    ptx = inb[2]
    pty = inb[3]
    ret2 = transform_point(ptx,pty,inepsg,outepsg) 
    return([ret1[0],ret1[1],ret2[0],ret2[1]])

def transform_point(ptx,pty,inepsg,outepsg):
    inProj = Proj(init='epsg:{}'.format(inepsg))
    outProj = Proj(init='epsg:{}'.format(outepsg))
    x1,y1 = ptx,pty
    x2,y2 = transform(inProj,outProj,x1,y1)
    return([x2,y2])

def reproject_wkt(wkt, in_epsg, out_epsg):

    source = osr.SpatialReference()
    source.ImportFromEPSG(in_epsg)

    target = osr.SpatialReference()
    target.ImportFromEPSG(out_epsg)

    transform = osr.CoordinateTransformation(source, target)

    geom = ogr.CreateGeometryFromWkt(wkt)
    geom.Transform(transform)

    return(geom.ExportToWkt())


def get_best_dem(y_min,y_max,x_min,x_max,demName=None):

    driver = ogr.GetDriverByName('ESRI Shapefile')
    shpdir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "config"))

    # Read in the DEM list
    dem_list = []
    myfile = os.path.join(shpdir,"get_dem.py.cfg")
    with open(myfile) as f:
        content = f.readlines()
        for item in content:
            dem_list.append([item.split()[0],item.split()[2]]) 
    logging.info("dem_list {}".format(dem_list))

    # If a dem is specified, use it instead of the list
    if demName:
        new_dem_list = []
        for item in dem_list:
            if demName in item[0] and len(demName)==len(item[0]):
                new_dem_list.append([demName,item[1]])
        dem_list = new_dem_list

    scene_wkt = "POLYGON ((%s %s, %s %s, %s %s, %s %s, %s %s))" % (x_min,y_min,x_max,y_min,x_max,y_max,x_min,y_max,x_min,y_min)

    best_pct = 0
    best_dem = ""
    best_tile_list = []

    for item in dem_list:
        DEM = item[0].lower()
        demEPSG = int(item[1])
        if demEPSG != 4326:
            logging.info("Reprojecting corners into projection {}".format(demEPSG))
            proj_wkt = reproject_wkt(scene_wkt,4326,int(demEPSG))
        else:
            proj_wkt = scene_wkt 
                
        dataset = driver.Open(os.path.join(shpdir,DEM+'_coverage.shp'), 0)
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
                logging.info("Working on tile {}".format(tile))
                coverage += a
                tiles += "," + tile
                tile_list.append(tile)

        logging.info("Totals: {} {} {} {}".format(DEM, coverage, total_area,
          coverage/total_area))
        pct = coverage/total_area
        if pct >= .99:
            best_dem = DEM.upper() + tiles
            best_pct = pct
            best_name = DEM.upper()
            best_tile_list = tile_list
            best_epsg = demEPSG
            best_poly_list = poly_list
            break
        if best_pct == 0 or pct > best_pct+0.05:
            best_dem = DEM.upper() + tiles
            best_pct = pct
            best_name = DEM.upper()
            best_tile_list = tile_list
            best_epsg = demEPSG
            best_poly_list = poly_list

    if best_pct < .20:
        logging.error("ERROR: Unable to find a DEM file for that area")
        sys.exit(1)
    logging.info("Best DEM: {}".format(best_name))
    logging.info("Tile List: {}".format(best_tile_list))
    return(best_name, best_epsg, best_tile_list, best_poly_list)

def get_tile_for(args):
    demname, fi = args
    cfgdir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "config"))
    myfile = os.path.join(cfgdir,"get_dem.py.cfg")

    with open(myfile) as f:
        content = f.readlines()
        for item in content:
            if demname in item.split()[0] and len(demname) == len(item.split()[0]):
                (mydir,myfile) = os.path.split(item)
                mydir = mydir.split()[1]
                if "s3" in mydir:
                    myfile = os.path.join(demname,fi)+".tif"
                    s3 = boto3.resource('s3')
                    s3.meta.client.meta.events.register('choose-signer.s3.*', disable_signing)
                    mybucket = mydir.split("/")[-1]
                    s3.Bucket(mybucket).download_file(myfile,"DEM/{}.tif".format(fi))
                else:
                    myfile = os.path.join(mydir,demname,"geotiff",fi) + ".tif"
                    output = "DEM/%s" % fi + ".tif"
                    shutil.copy(myfile, output)


def parseString(string):
    l = string.split("(")
    m = l[1].split(",")
    n = m[0]
    o = m[1].split(")")[0]
    return(float(n),float(o))


def get_cc(tmpproj,post,pixsize):

    shift = 0
    string = subprocess.check_output('gdalinfo %s' % tmpproj, shell=True).decode()
    lst = string.split("\n")
    for item in lst:
        if "Upper Left" in item:
            (east1,north1) = parseString(item)
        if "Lower Left" in item:
            (east2,north2) = parseString(item)
        if "Upper Right" in item:
            (east3,north3) = parseString(item)
        if "Lower Right" in item:
            (east4,north4) = parseString(item)

    e_min = min(east1,east2,east3,east4)
    e_max = max(east1,east2,east3,east4)
    n_min = min(north1,north2,north3,north4)
    n_max = max(north1,north2,north3,north4)

    e_max = math.ceil(e_max/post)*post+shift
    e_min = math.floor(e_min/post)*post-shift
    n_max = math.ceil(n_max/post)*post+shift
    n_min = math.floor(n_min/post)*post-shift

    logging.info("New coordinates: %f %f %f %f" % (e_max,e_min,n_max,n_min))
    return(e_min,e_max,n_min,n_max)


def handle_anti_meridian(y_min,y_max,x_min,x_max,outfile):
    logging.info("Handling using anti-meridian special code")
    if (y_min>49 and y_max<54):
        logging.info("DEM will be SRTMUS1")
        anti_meridian_kludge("SRTMUS1_zone1.tif","SRTMUS1","",y_min,y_max,x_min,x_max,outfile);
    elif (y_min>-52 and y_max<-6):
        logging.info("DEM will be SRTMGL3")
        anti_meridian_kludge("SRTMGL3_zone1.tif","SRTMGL3","+south",y_min,y_max,x_min,x_max,outfile);
    else:
        logging.error("ERROR: Unable to find a DEM")
        sys.exit(1)

def anti_meridian_kludge(dem_file,dem_name,south,y_min,y_max,x_min,x_max,outfile):

    # Get the appropriate file
    cfgdir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "config"))
    myfile = os.path.join(cfgdir,"get_dem.py.cfg")
    with open(myfile) as f:
        content = f.readlines()
        for item in content:
            if dem_name in item:
                (mydir,myfile) = os.path.split(item)
                mydir = mydir.split()[1]
                if "s3" in mydir:
                    myfile = os.path.join(dem_name,dem_file)
                    s3 = boto3.resource('s3')
                    s3.meta.client.meta.events.register('choose-signer.s3.*', disable_signing)
                    mybucket = mydir.split("/")[-1]
                    s3.Bucket(mybucket).download_file(myfile,"DEM/{}".format(dem_file))
                else:
                    myfile = os.path.join(mydir,dem_file)
                    logging.info("Tile: {}".format(myfile))
                    shutil.copy(myfile,".")

    if not os.path.isfile(dem_file):
        logging.error("ERROR: unable to copy DEM file")
        sys.exit(1)

    # Now project lat/lon extents into UTM
    f = open("coords.txt","w")
    f.write("%f %f\n" % (x_min,y_min))
    f.write("%f %f\n" % (x_min,y_max))
    f.write("%f %f\n" % (x_max,y_min))
    f.write("%f %f\n" % (x_max,y_max))
    f.close()

    string = subprocess.check_output("cat coords.txt | cs2cs +proj=longlat +datum=WGS84 +to +proj=utm +zone=1 %s +datum=WGS84" % south, shell=True).decode()
    lst = string.split("\n")
    x = []
    y = []
    for i in range(len(lst)):
        l = lst[i].split("\t")
        x.append(l[0])
        y.append(l[1].split()[0])

    e_min = float(min(x))
    e_max = float(max(x))
    n_min = float(min(y))
    n_max = float(max(y))

    if len(south) > 0:
        n_min = n_min - 10000000.0
        n_max = n_max - 10000000.0

    bounds = [e_min,n_min,e_max,n_max]
    logging.info("Creating output file {} with bounds {}".format(outfile,bounds))
    gdal.Warp(outfile,dem_file,outputBounds=bounds,resampleAlg="cubic",dstNodata=-32767)

def writeVRT(dem_proj, nodata, tile_list, poly_list, outFile):

    # Get dimensions and pixel size from first DEM in tile ListCommand
    demFile = os.path.join('DEM', '{0}.tif'.format(tile_list[0]))
    (spatialRef, gt, shape, pixel) = raster_meta(demFile)
    (rows, cols) = shape
    pixSize = gt[1]

    # Determine coverage
    minLon = 360
    maxLon = -180
    minLat = 90
    maxLat = -90
    for poly in poly_list:
        polygon = ogr.CreateGeometryFromWkt(poly)
        envelope = polygon.GetEnvelope()
        if envelope[0] < minLon: minLon = envelope[0]
        if envelope[1] > maxLon: maxLon = envelope[1]
        if envelope[2] < minLat: minLat = envelope[2]
        if envelope[3] > maxLat: maxLat = envelope[3]
    rasterXSize = np.int(np.rint((maxLon-minLon)/pixSize)) + 1
    rasterYSize = np.int(np.rint((maxLat-minLat)/pixSize)) + 1

    # Determine offsets
    offsetX = []
    offsetY = []
    for poly in poly_list:
        polygon = ogr.CreateGeometryFromWkt(poly)
        envelope = polygon.GetEnvelope()
        offsetX.append(np.int(np.rint((envelope[0] - minLon)/pixSize)))
        offsetY.append(np.int(np.rint((maxLat - envelope[3])/pixSize)))

    # Generate XML structure
    vrt = et.Element('VRTDataset', rasterXSize=str(rasterXSize),
        rasterYSize=str(rasterYSize))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(dem_proj)
    et.SubElement(vrt, 'SRS').text = srs.ExportToWkt()
    geoTrans = ('%.16f, %.16f, 0.0, %.16f, 0.0, %.16f' % (minLon, pixSize, maxLat,
        -pixSize))
    et.SubElement(vrt, 'GeoTransform').text = geoTrans
    bands = et.SubElement(vrt, 'VRTRasterBand', dataType='Float32', band='1')
    et.SubElement(bands, 'NoDataValue').text = '-32768'
    et.SubElement(bands, 'ColorInterp').text = 'Gray'
    tileCount = len(tile_list)
    for ii in range(tileCount):
        source = et.SubElement(bands, 'ComplexSource')
        demFile = os.path.join('DEM', '{0}.tif'.format(tile_list[ii]))
        et.SubElement(source, 'SourceFilename', relativeToVRT='1').text = \
            demFile
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
        dst.set('xOff', str(offsetX[ii]))
        dst.set('yOff', str(offsetY[ii]))
        dst.set('xSize', str(cols))
        dst.set('ySize', str(rows))
        et.SubElement(source, 'NODATA').text = "{}".format(nodata)

    # Write VRT file
    with open(outFile, 'w') as outF:
        outF.write(et.tostring(vrt, xml_declaration=False, encoding='utf-8',
            pretty_print=True))
        outF.close()


# GET DEM file and convert into ISCE format
def get_ISCE_dem(west,south,east,north,demName,demXMLName):
    # Get the DEM file
    chosen_dem = get_dem(west,south,east,north,"temp_dem.tif")

    # Reproject DEM into Lat, Lon space
    pixsize = 0.000277777777778
    gdal.Warp(demName,"temp_dem.tif",format="ENVI",dstSRS="EPSG:4326",xRes=pixsize,yRes=pixsize,resampleAlg="cubic",dstNodata=-32767)
    ext = os.path.splitext(demName)[1]
    hdrName = demName.replace(ext,".hdr")
    dem2isce.dem2isce(demName,hdrName,demXMLName)
    return chosen_dem

# GET DEM file and convert into lat,lon format
def get_ll_dem(west,south,east,north,outDem,post=None,processes=1,demName=None,leave=False):
    demType = get_dem(west,south,east,north,"temp_dem.tif",post=post,processes=processes,demName=demName,leave=leave)
    pixsize = 0.000277777777778
    gdal.Warp(outDem,"temp_dem.tif",dstSRS="EPSG:4326",xRes=pixsize,yRes=pixsize,resampleAlg="cubic",dstNodata=-32767)
    os.remove("temp_dem.tif")
    return(demType)

# Main external entry point
def get_dem(x_min,y_min,x_max,y_max,outfile,post=None,processes=1,demName=None,leave=False):

    if post is not None:
        logging.info("Snapping to grid at posting of %s meters" % post)

    if x_min < -180 or x_max > 180:
        logging.error("ERROR: Please using longitude in range (-180,180) %s %s" % (y_min,x_max))
        sys.exit(1)

    if y_min < -90 or y_max > 90:
        loggging.error("ERROR: Please use latitude in range (-90,90) %s %s" % (y_min,y_max))
        sys.exit(1)

    if x_min > x_max:
        logging.warning("WARNING: minimum easting > maximum easting - swapping")
        (x_min, x_max) = (x_max, x_min)

    if y_min > y_max:
        logging.warning("WARNING: minimum northing > maximum northing - swapping")
        (y_min, y_max) = (y_max, y_min)

    # Figure out which DEM and get the tile list
    (demname, demproj, tile_list, poly_list) = get_best_dem(y_min,y_max,x_min,x_max,demName=demName)
    demproj = int(demproj)
    logging.info("demproj is {}".format(demproj))

    # Add buffer for REMA
    if 'REMA' in demname or 'GIMP' in demname or 'EU_DEM' in demname
        y_min -= 2
        y_max += 2
        x_min -= 2
        x_max += 2

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

    #os.system("gdalbuildvrt temp.vrt DEM/*.tif")
    if "SRTMGL1" in demname:
        nodata = -32768
    elif "GIMP" in demname:
        nodata = None
    elif "REMA" in demname:
        nodata = 0
    elif "NED" in demname or "EU_DEM_V11" in demname:
        nodata = -3.4028234663852886e+38 

    writeVRT(demproj, nodata, tile_list, poly_list, 'temp.vrt')
 
#
#   Set the output projection to either NPS, SPS, or UTM
#
    if demproj == 3413: 	# North Polar Stereo
        outproj = ('EPSG:3413')
        outproj_num = 3413
    elif demproj == 3031:        # South Polar Stereo
        outproj = ('EPSG:3031')
        outproj_num = 3031
    else:
        lon = (x_max+x_min)/2
        zone = math.floor((lon+180)/6+1)
        if (y_min+y_max)/2 > 0:
            outproj = ('EPSG:326%02d' % int(zone))
            outproj_num = int("326%02d"%int(zone))
        else:
            outproj = ('EPSG:327%02d' % int(zone))
            outproj_num = int("327%02d"%int(zone))
     
    tmpdem = "tempdem.tif"
    tmpdem2 = "tempdem2.tif"
    tmpproj = "tmpproj.tif"
    if os.path.isfile(tmpdem):
        logging.info("Removing old file tmpdem")
        os.remove(tmpdem)
    if os.path.isfile(tmpproj):
        logging.info("Removing old file projected dem file")
        os.remove(tmpproj)

    pixsize = 30.0
    gcssize = 0.00027777777778

    if demname == "SRTMGL3":
        pixsize = 90.
        gcssize = gcssize * 3
    if demname == "NED2":
        pixsize = 60.
        gcssize = gcssize * 2

    bounds = [x_min,y_min,x_max,y_max]

    logging.info("Creating initial raster file")
    logging.info("    tmpdem {t}".format(t=tmpdem))
    logging.info("    pixsize {p}".format(p=pixsize))
    logging.info("    bounds {b}".format(b=bounds))

    # xform bounds to projection of the DEM
    if demproj != 4326:
        bounds = transform_bounds(bounds,4326,demproj)
        logging.info("    transformed bounds {b}".format(b=bounds))
        if bounds[0] > bounds[2]:
            (bounds[0], bounds[2]) = (bounds[2], bounds[0])
        if bounds[1] > bounds[3]:
            (bounds[1], bounds[3]) = (bounds[3], bounds[1])

    if demproj == 4269 or demproj == 4326:
        gdal.Warp(tmpdem,"temp.vrt",xRes=gcssize,yRes=gcssize,outputBounds=bounds,resampleAlg="cubic",dstNodata=-32767)
    else:
        gdal.Warp(tmpdem,"temp.vrt",xRes=pixsize,yRes=pixsize,outputBounds=bounds,resampleAlg="cubic",dstNodata=-32767)

    # If DEM is from NED collection, then it will have a NAD83 ellipse -
    # need to convert to WGS84
    # Also, need to convert from pixel as area to pixel as point
    if "NED" in demname:
        logging.info("Converting to WGS84")
        gdal.Warp("temp_dem_wgs84.tif",tmpdem, dstSRS="EPSG:4326")
        logging.info("Converting to pixel as point")
        x1, y1, t1, p1, data = \
            saa.read_gdal_file(saa.open_gdal_file("temp_dem_wgs84.tif"))
        lon = t1[0]
        resx = t1[1]
        rotx = t1[2]
        lat = t1[3]
        roty = t1[4]
        resy = t1[5]
        lon = lon + resx/2.0
        lat = lat + resy/2.0
        t1 = [lon, resx, rotx, lat, roty, resy]
        saa.write_gdal_file_float(tmpdem,t1,p1,data)
        if not leave:
            os.remove("temp_dem_wgs84.tif")

    gdal.Translate(tmpdem2,tmpdem,metadataOptions = ['AREA_OR_POINT=Point'])
    shutil.move(tmpdem2,tmpdem)

    # Need to reproject the DEM file into UTM space
    if demproj != outproj_num:
        logging.info("Translating raster file to projected coordinates ({p})".format(p=outproj))
        gdal.Warp(tmpproj,tmpdem,dstSRS=outproj,xRes=pixsize,yRes=pixsize,resampleAlg="cubic",dstNodata=-32767)
        if post is not None:
            logging.info("Snapping file to grid at %s meters" % post)
            (e_min,e_max,n_min,n_max) = get_cc(tmpproj,post,pixsize)
            bounds = [e_min,n_min,e_max,n_max]
            gdal.Warp(outfile,tmpproj,xRes=pixsize,yRes=pixsize,outputBounds=bounds,resampleAlg="cubic",dstNodata=-32767)
        else:
            logging.info("Copying projected DEM to output file name")
            shutil.copy(tmpproj,outfile)
    else:
        if post is not None:
            logging.info("Snapping file to grid at %s meters" % post)
            (e_min,e_max,n_min,n_max) = get_cc(tmpdem,post,pixsize)
            bounds = [e_min,n_min,e_max,n_max]
            gdal.Warp(outfile,tmpdem,xRes=pixsize,yRes=pixsize,outputBounds=bounds,resampleAlg="cubic",dstNodata=-32767)
        else:
            logging.info("Copying DEM to output file name")
            shutil.copy(tmpdem,outfile)

    if not leave:
        if os.path.isfile(tmpdem):
            logging.info("Removing old file tmpdem")
            os.remove(tmpdem)
        if os.path.isfile(tmpproj):
            logging.info("Removing old file projected dem file")
            os.remove(tmpproj)

    logging.info("Successful Completion!")

    return(demname)


def positive_int(value):
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError("{} is an invalid positive int value".format(value))
    return ivalue

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="get_dem.py",
            description="Get a DEM file in .tif format from the ASF DEM heap")
    parser.add_argument("x_min",help="minimum longitude/easting",type=float)
    parser.add_argument("y_min",help="minimum latitude/northing",type=float)
    parser.add_argument("x_max",help="maximum longitude/easting",type=float)
    parser.add_argument("y_max",help="maximum latitude/northing",type=float)
    parser.add_argument("outfile",help="output DEM name")
    parser.add_argument("-p","--posting",type=float,help="Snap DEM to align with grid at given posting")
    parser.add_argument("-d","--dem",help="Type of DEM to use")
    parser.add_argument("-t", "--threads", type=positive_int, default=1,
        help="Num of threads to use for downloading DEM tiles")
    parser.add_argument("-l","--latlon", action='store_true',
        help="Create output in GCS coordinates (default is native DEM projection)")
    parser.add_argument("-k","--keep", action='store_true',help="Keep intermediate DEM results")
    args = parser.parse_args()

    logFile = "get_dem_{}.log".format(os.getpid())
    logging.basicConfig(filename=logFile,format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',level=logging.DEBUG)
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.info("Starting run")

    y_min = float(args.y_min)
    y_max = float(args.y_max)
    x_min = float(args.x_min)
    x_max = float(args.x_max)
    outfile = args.outfile

    if args.latlon:
        get_ll_dem(x_min,y_min,x_max,y_max,outfile,post=args.posting,
                   leave=args.keep,processes=args.threads,demName=args.dem)

    else:
        get_dem(x_min,y_min,x_max,y_max,outfile,post=args.posting,
                   leave=args.keep,processes=args.threads,demName=args.dem)

