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
from osgeo import gdal
import argparse
import boto3
from botocore.handlers import disable_signing
import subprocess
import dem2isce
import saa_func_lib as saa
import multiprocessing as mp


def get_best_dem(lat_min,lat_max,lon_min,lon_max):

    driver = ogr.GetDriverByName('ESRI Shapefile')
    shpdir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "config"))

    scene_wkt = "POLYGON ((%s %s, %s %s, %s %s, %s %s, %s %s))" % (lon_min,lat_min,lon_max,lat_min,lon_max,lat_max,lon_min,lat_max,lon_min,lat_min)

    best_pct = 0
    best_dem = ""
    best_tile_list = []

    for DEM in ['ned13','srtmgl1','srtmau1','ned1','ned2','srtmgl3']:
        dataset = driver.Open(os.path.join(shpdir,DEM+'_coverage.shp'), 0)
        poly = ogr.CreateGeometryFromWkt(scene_wkt)
        total_area = poly.GetArea()

        coverage = 0
        tiles = ""
        tile_list = []
        layer = dataset.GetLayer()
        for i in range(layer.GetFeatureCount()):
            feature = layer.GetFeature(i)
            wkt = feature.GetGeometryRef().ExportToWkt()
            tile_poly = ogr.CreateGeometryFromWkt(wkt)
            intersect = tile_poly.Intersection(poly)
            a = intersect.GetArea()
            if a > 0:
                tile = str(feature.GetFieldAsString(feature.GetFieldIndex("tile")))
                # print DEM,a,tile
                coverage += a
                tiles += "," + tile
                tile_list.append(tile)

        print("Total",DEM,coverage,total_area,coverage/total_area)
        pct = coverage/total_area
        if pct >= .99:
            # print "setting dem to %s" % (DEM.upper() + tiles)
            best_dem = DEM.upper() + tiles
            best_pct = pct
            best_name = DEM.upper()
            best_tile_list = tile_list
            break
        if best_pct == 0 or pct > best_pct+0.05:
            # print "Setting %s to best dem; pct = %f" % (DEM.upper(),pct)
            best_dem = DEM.upper() + tiles
            best_pct = pct
            best_name = DEM.upper()
            best_tile_list = tile_list

    if best_pct < .20:
        print("ERROR: Unable to find a DEM file for that area")
        sys.exit(1)
    print(best_name)
    print(best_tile_list)
    return(best_name, best_tile_list)

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
                    myfile = os.path.join(mydir,"geotiff",fi) + ".tif"
                    output = "DEM/%s" % fi + ".tif"
                    shutil.copy(myfile, output)


def parseString(string):
    l = string.split("(")
    m = l[1].split(",")
    n = m[0]
    o = m[1].split(")")[0]
    return(float(n),float(o))


def get_cc(tmputm,post,pixsize):

    shift = 0
    string = subprocess.check_output('gdalinfo %s' % tmputm, shell=True).decode()
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

    print("New coordinates: %f %f %f %f" % (e_max,e_min,n_max,n_min))
    return(e_min,e_max,n_min,n_max)


def handle_anti_meridian(lat_min,lat_max,lon_min,lon_max,outfile):
    print("Handling using anti-meridian special code")
    if (lat_min>49 and lat_max<54):
        print("DEM will be SRTMUS1")
        anti_meridian_kludge("SRTMUS1_zone1.tif","SRTMUS1","",lat_min,lat_max,lon_min,lon_max,outfile);
    elif (lat_min>-52 and lat_max<-6):
        print("DEM will be SRTMGL3")
        anti_meridian_kludge("SRTMGL3_zone1.tif","SRTMGL3","+south",lat_min,lat_max,lon_min,lon_max,outfile);
    else:
        print("ERROR: Unable to find a DEM")
        sys.exit(1)

def anti_meridian_kludge(dem_file,dem_name,south,lat_min,lat_max,lon_min,lon_max,outfile):

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
                    s3.Bucket(mybucket).download_file(myfile,"DEM/{}.tif".format(fi))
                else:
                    myfile = os.path.join(mydir,dem_file)
                    print(myfile)
                    shutil.copy(myfile,".")

    if not os.path.isfile(dem_file):
        print("ERROR: unable to copy DEM file")
        sys.exit(1)

    # Now project lat/lon extents into UTM
    f = open("coords.txt","w")
    f.write("%f %f\n" % (lon_min,lat_min))
    f.write("%f %f\n" % (lon_min,lat_max))
    f.write("%f %f\n" % (lon_max,lat_min))
    f.write("%f %f\n" % (lon_max,lat_max))
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
    print("Creating output file {} with bounds {}".format(outfile,bounds))
    gdal.Warp(outfile,dem_file,outputBounds=bounds,resampleAlg="cubic",dstNodata=-32767)

# GET DEM file and convert into ISCE format
def get_ISCE_dem(west,south,east,north,demName,demXMLName):
        get_dem(west,south,east,north,"temp_dem.tif",False)
        gdal.Translate(demName,"temp_dem.tif",format="ENVI")
        ext = os.path.splitext(demName)[1]
        hdrName = demName.replace(ext,".hdr")
        dem2isce.dem2isce(demName,hdrName,demXMLName)

def get_dem(lon_min,lat_min,lon_max,lat_max,outfile,utmflag,post=None, processes=1):

    if post is not None:
        if not utmflag:
            print("ERROR: May use posting with UTM projection only")
            sys.exit(1)
        posting = post
        print("Snapping to grid at posting of %s meters" % posting)

    if lon_min < -180 or lon_max > 180:
        print("lon_min = %f; lon_max = %f" % (lon_min,lon_max))
        print("ERROR: Please using longitude in range (-180,180)")
        sys.exit(1)

    if lat_min < -90 or lat_max > 90:
        print("ERROR: Please use latitude in range (-90,90) %s %s" % (lat_min,lat_max))
        sys.exit(1)

    if lon_min > lon_max:
        print("WARNING: minimum longitude > maximum longitude - swapping")
        (lon_min, lon_max) = (lon_max, lon_min)

    if lat_min > lat_max:
        print("WARNING: minimum latitude > maximum latitude - swapping")
        (lat_min, lat_max) = (lat_max, lat_min)

    # Handle cases near anti-meridian
    if lon_min <= -178 and lon_max >= 178:
        if utmflag:
            handle_anti_meridian(lat_min,lat_max,lon_min,lon_max,outfile)
            return(0)
        else:
            print("ERROR: May only create a DEM file over anti-meridian using UTM coordinates")
            sys.exit(1)

    # Figure out which DEM and get the tile list
    (demname, tile_list) = get_best_dem(lat_min,lat_max,lon_min,lon_max)

    # Copy the files into a dem directory
    if not os.path.isdir("DEM"):
        os.mkdir("DEM")

    # Download tiles in parallel
    p = mp.Pool(processes=processes)
    p.map(
        get_tile_for,
        [(demname, fi) for fi in tile_list]
    )


    os.system("gdalbuildvrt temp.vrt DEM/*.tif")

    lon = (lon_max+lon_min)/2
    zone = math.floor((lon+180)/6+1)
    if (lat_min+lat_max)/2 > 0:
        hemi = "N"
        proj = ('EPSG:326%02d' % int(zone))
    else:
        hemi = "S"
        proj = ('EPSG:327%02d' % int(zone))

    tmpdem = "tempdem.tif"
    tmpdem2 = "tempdem2.tif"
    tmputm = "temputm.tif"
    if os.path.isfile(tmpdem):
        print("Removing old file tmpdem")
        os.remove(tmpdem)
    if os.path.isfile(tmputm):
        print("Removing old file utmdem")
        os.remove(tmputm)

    pixsize = 30.0
    gcssize = 0.00027777777778

    if demname == "SRTMGL3":
        pixsize = 90.
        gcssize = gcssize * 3
    if demname == "NED2":
        pixsize = 60.
        gcssize = gcssize * 2

    bounds = [lon_min,lat_min,lon_max,lat_max]

    print("Creating initial raster file")
    gdal.Warp(tmpdem,"temp.vrt",xRes=gcssize,yRes=gcssize,outputBounds=bounds,resampleAlg="cubic",dstNodata=-32767)

    # If DEM is from NED collection, then it will have a NAD83 ellipse - need to convert to WGS84
    # Also, need to convert from pixel as area to pixel as point
    if "NED" in demname:
        print("Converting to WGS84")
        gdal.Warp("temp_dem_wgs84.tif",tmpdem, dstSRS="EPSG:4326")
        print("Converting to pixel as point")
        x1,y1,t1,p1,data = saa.read_gdal_file(saa.open_gdal_file("temp_dem_wgs84.tif"))
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

    gdal.Translate(tmpdem2,tmpdem,metadataOptions = ['AREA_OR_POINT=Point'])
    shutil.move(tmpdem2,tmpdem)

    if utmflag:
        print("Translating raster file to UTM coordinates")
        gdal.Warp(tmputm,tmpdem,dstSRS=proj,xRes=pixsize,yRes=pixsize,resampleAlg="cubic",dstNodata=-32767)
        if post is not None:
            print("Snapping file to grid at %s meters" % posting)
            (e_min,e_max,n_min,n_max) = get_cc(tmputm,posting,pixsize)
            bounds = [e_min,n_min,e_max,n_max]
            gdal.Warp(outfile,tmputm,xRes=pixsize,yRes=pixsize,outputBounds=bounds,resampleAlg="cubic",dstNodata=-32767)
        else:
            os.rename(tmputm,outfile)
    else:
        os.rename(tmpdem,outfile)

    return(demname)


def positive_int(value):
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError("{} is an invalid positive int value".format(value))
    return ivalue

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="get_dem.py",description="Get a DEM file in .tif format from the ASF DEM heap")
    parser.add_argument("lon_min",help="minimum longitude",type=float)
    parser.add_argument("lat_min",help="minimum latitude",type=float)
    parser.add_argument("lon_max",help="maximum longitude",type=float)
    parser.add_argument("lat_max",help="maximum latitude",type=float)
    parser.add_argument("outfile",help="output DEM name")
    parser.add_argument("-u","--utm",action='store_true',help="Create output in UTM projection")
    parser.add_argument("-p","--posting",type=float,help="Snap DEM to align with grid at given posting")
    parser.add_argument("--aws", action='store_const', const=True, help="use aws config file")
    parser.add_argument("-t", "--threads", type=positive_int, default=1,
            help="Num of threads to use for downloading DEM tiles")
    args = parser.parse_args()

    lat_min = float(args.lat_min)
    lat_max = float(args.lat_max)
    lon_min = float(args.lon_min)
    lon_max = float(args.lon_max)
    outfile = args.outfile
    utmflag = args.utm
    use_aws_config = args.aws if args.aws else False

    if args.posting is not None:
        get_dem(lon_min,lat_min,lon_max,lat_max,outfile,utmflag,post=args.posting, processes=args.threads)
    else:
        get_dem(lon_min,lat_min,lon_max,lat_max,outfile,utmflag, processes=args.threads)


