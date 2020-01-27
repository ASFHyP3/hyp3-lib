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
import get_dem
import os
import sys
import argparse
from getSubSwath import get_bounding_box_file
from execute import execute
from osgeo import gdal
import shutil
import logging
from saa_func_lib import get_utm_proj

def getDemFile(infile,outfile,opentopoFlag=None,utmFlag=True,post=None,demName=None):
    lat_max,lat_min,lon_max,lon_min = get_bounding_box_file(infile)
    if opentopoFlag:
        cmd = "wget -O%s \"http://opentopo.sdsc.edu/otr/getdem?demtype=SRTMGL1&west=%s&south=%s&east=%s&north=%s&outputFormat=GTiff\"" % (outfile,lon_min,lat_min,lon_max,lat_max)
        execute(cmd)
        if utmFlag:
            proj = get_utm_proj(lon_min,lon_max,lat_min,lat_max)
            tmpdem = "tmpdem_getDemFile_utm.tif"
            gdal.Warp("%s" %tmpdem,"%s" % outfile,dstSRS=proj,resampleAlg="cubic")
            shutil.move(tmpdem,"%s" % outfile)
    else:
        if utmFlag:
            logging.debug("Calling get_dem with outfile of {}".format(outfile))
            demtype = get_dem.get_dem(lon_min,lat_min,lon_max,lat_max,outfile,post=post,demName=demName)
            if not os.path.isfile(outfile):
                logging.error("Unable to find output file {}".format(outfile))
        else:
            demtype = get_dem.get_ll_dem(lon_min,lat_min,lon_max,lat_max,outfile,post=post,demName=demName)
            
    return(outfile,demtype)
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Get a DEM file for a given sentinel1 SAFE file")
    parser.add_argument("SAFEfile",help="S1 SAFE file")
    parser.add_argument("outfile",help="Name of output geotiff DEM file")
    parser.add_argument("-o","--opentopo",action="store_true",help="Use opentopo instead of get_dem")
    parser.add_argument("-l","--latlon",action="store_false",
        help="Create DEM in lat,lon space - dangerous option for polar imagery")
    parser.add_argument("-d","--dem",help="Only use the specified DEM type")
    parser.add_argument("-p","--post",help="Posting for creating DEM",type=float)
    args = parser.parse_args()

    logFile = "getDemFor_{}.log".format(os.getpid())
    logging.basicConfig(filename=logFile,format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',level=logging.DEBUG)
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.info("Starting run")

    outfile,demtype = getDemFile(args.SAFEfile,args.outfile,opentopoFlag=args.opentopo,
                                 utmFlag=args.latlon,post=args.post,demName=args.dem)
    logging.info("Wrote DEM file %s" % outfile)
