#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
###############################################################################
# CutGeotiffs
#
# Project:  APD 
# Purpose:  Cut out a bunch of geotiffs to the same area
#  
# Author:   Tom Logan
#
# Issues/Caveats:
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
import saa_func_lib as saa
import re
import argparse
from osgeo import gdal

def getPixSize(fi):
    (x1,y1,t1,p1) = saa.read_gdal_file_geo(saa.open_gdal_file(fi))
    return (t1[1])

def getCorners(fi):
    (x1,y1,t1,p1) = saa.read_gdal_file_geo(saa.open_gdal_file(fi))
    ullon1 = t1[0]
    ullat1 = t1[3]
    lrlon1 = t1[0] + x1*t1[1]
    lrlat1 = t1[3] + y1*t1[5]
    return (ullon1,ullat1,lrlon1,lrlat1)

def getOverlap(coords,fi):
    (x1,y1,t1,p1) = saa.read_gdal_file_geo(saa.open_gdal_file(fi))

    ullon1 = t1[0]
    ullat1 = t1[3]
    lrlon1 = t1[0] + x1*t1[1]
    lrlat1 = t1[3] + y1*t1[5]

    ullon2 = coords[0]
    ullat2 = coords[1]
    lrlon2 = coords[2]
    lrlat2 = coords[3]

    ullat = min(ullat1,ullat2)
    ullon = max(ullon1,ullon2)
    lrlat = max(lrlat1,lrlat2)
    lrlon = min(lrlon1,lrlon2)

    return (ullon,ullat,lrlon,lrlat)

def cutFiles(arg):

    if len(arg) == 1:
        print "Nothing to do!!!  Exiting..."
        exit(0)

    file1 = arg[0]
    print "Clipping geotiff files starting with %s as the base." % file1
   
    # Open file1, get projection and pixsize
    dst1 = gdal.Open(file1)
    p1 = dst1.GetProjection()
    print p1
    
    # Make sure that UTM projections match
    ptr = p1.find("UTM zone ")
    if ptr != -1:
        (zone1,hemi) = [t(s) for t,s in zip((int,str), re.search("(\d+)(.)",p1[ptr:]).groups())]
        for x in range(len(arg)-1):
            file2 = arg[x+1]

            # Open up file2, get projection 
            dst2 = gdal.Open(file2)
            p2 = dst2.GetProjection()

            # Cut the UTM zone out of projection2 
            ptr = p2.find("UTM zone ")
            zone2 = re.search("(\d+)",p2[ptr:]).groups()
            zone2 = int(zone2[0])

            if zone1 != zone2:
                print "Projections don't match... Reprojecting %s" % file2
                if hemi == "N":
                    proj = ('EPSG:326%02d' % int(zone1))
                else:
                    proj = ('EPSG:327%02d' % int(zone1))
	        print "    reprojecting post image"
                print "    proj is %s" % proj
                name = file2.replace(".tif","_reproj.tif")
                gdal.Warp(name,file2,dstSRS=proj,xRes=pixsize,yRes=pixsize)
                arg[x+1] = name

    # Find the overlap between all scenes
    coords = getCorners(arg[0])
    for x in range (len(arg)-1):
        coords = getOverlap(coords,arg[x+1])
    
    # Find the largest pixel size of all scenes
    pixSize = getPixSize(arg[0])
    for x in range (len(arg)-1):
        tmp = getPixSize(arg[x+1])
	pixSize = max(pixSize,tmp)
     
    # Finally, clip all scenes to the overlap region at the largest pixel size
    for x in range (len(arg)):
        file1 = arg[x]
        file1_new = file1.replace('.tif','_clip.tif')
        dst_d1 = gdal.Translate(file1_new,file1,projWin=coords,xRes=pixSize,yRes=pixSize,creationOptions = ['COMPRESS=LZW'])


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Clip a bunch of geotiffs to the same area.")
    parser.add_argument("infiles",nargs='+',help="Geotiff files to clip; output will be have _clip appended to the file name")
    args = parser.parse_args()
    cutFiles(args.infiles)
