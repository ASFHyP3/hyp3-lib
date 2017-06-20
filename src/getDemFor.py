#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
###############################################################################
# getDemFor.py
#
# Project:  APD general tool
# Purpose:  Get a DEM for a given Sentinel1 scene
#          
# Author:   Tom Logan
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

#####################
#
# Import all needed modules right away
#
#####################
from lxml import etree
import get_dem
import os
import argparse
from getSubSwath import get_bounding_box

def getDemFile(infile,utmflag):
    mydir = "%s/annotation" %  infile
    myxml = ""
    name = ""

    # Get corners from first and last swath
    name = "001.xml"
    for myfile in os.listdir(mydir):
        if name in myfile:
            myxml = "%s/annotation/%s" % (infile,myfile)
    (lat1,lat2,lon1,lon2) = get_bounding_box(myxml)
    lat1 = lat1 + 0.15;
    lat2 = lat2 - 0.15;
    lon1 = lon1 + 0.15;
    lon2 = lon2 - 0.15;

    name = "003.xml"
    for myfile in os.listdir(mydir):
        if name in myfile:
            myxml = "%s/annotation/%s" % (infile,myfile)
    (lat3,lat4,lon3,lon4) = get_bounding_box(myxml)
    lat3 = lat3 + 0.15;
    lat4 = lat4 - 0.15;
    lon3 = lon3 + 0.15;
    lon4 = lon4 - 0.15;

    lon_max = -180
    lon_min = 180
    lat_max = -90
    lat_min = 90

    lat_max = max(lat1,lat2,lat3,lat4)
    lat_min = min(lat1,lat2,lat3,lat4)
    lon_max = max(lon1,lon2,lon3,lon4)
    lon_min = min(lon1,lon2,lon3,lon4)
    
    get_dem.get_dem(lon_min,lat_min,lon_max,lat_max,"area_dem.tif",utmflag)

    return("area_dem.tif")
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Get a DEM file for a given sentinel1 SAFE file")
    parser.add_argument("SAFEfile",help="S1 SAFE file")
    parser.add_argument("-u","--utm",action="store_true",help="Make DEM file in UTM coordinates (defaults is GCS)")
    args = parser.parse_args()

    outfile = getDemFile(args.SAFEfile,args.utm)
    print "Wrote DEM file %s" % outfile
    
     
     
