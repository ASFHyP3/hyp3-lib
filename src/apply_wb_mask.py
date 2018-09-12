#!/usr/bin/python

import os
import numpy as np
import scipy.misc
import argparse
import logging
import shutil
from osgeo import gdal
from create_wb_mask import create_wb_mask
import saa_func_lib as saa
from osgeo.gdalconst import *

def create_wb_mask_file(xmin,ymin,xmax,ymax,res):

    cfgdir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "config")) 
    myfile = os.path.join(cfgdir,"shapefile_dir.txt")
    f = open(myfile,"r")
    for line in f.readlines():
        cfgdir = line.strip()

    shpfile = "{}/GSHHG_shp/f/GSHHS_f_L1.shp".format(cfgdir)
    mask1 = create_wb_mask(shpfile,xmin,ymin,xmax,ymax,res,outFile="mask1.png")
    shpfile = "{}/GSHHG_shp/f/GSHHS_f_L2.shp".format(cfgdir)
    mask2 = create_wb_mask(shpfile,xmin,ymin,xmax,ymax,res,outFile="mask2.png")
    shpfile = "{}/GSHHG_shp/f/GSHHS_f_L3.shp".format(cfgdir)
    mask3 = create_wb_mask(shpfile,xmin,ymin,xmax,ymax,res,outFile="mask3.png")
    shpfile = "{}/GSHHG_shp/f/GSHHS_f_L4.shp".format(cfgdir)
    mask4 = create_wb_mask(shpfile,xmin,ymin,xmax,ymax,res,outFile="mask4.png")
    shpfile = "{}/GSHHG_shp/f/GSHHS_f_L5.shp".format(cfgdir)
    mask5 = create_wb_mask(shpfile,xmin,ymin,xmax,ymax,res,outFile="mask5.png")
    shpfile = "{}/GSHHG_shp/f/GSHHS_f_L6.shp".format(cfgdir)
    mask6 = create_wb_mask(shpfile,xmin,ymin,xmax,ymax,res,outFile="mask6.png")

    mask2 = np.logical_not(mask2)
    mask3 = np.logical_not(mask3)
    mask4 = np.logical_not(mask4)
    mask5 = np.logical_not(mask5)
    mask6 = np.logical_not(mask6)

    final_mask = np.logical_and(mask1,mask2)
    final_mask = np.logical_and(final_mask,mask3)
    final_mask = np.logical_and(final_mask,mask4)
    final_mask = np.logical_and(final_mask,mask5)
    final_mask = np.logical_and(final_mask,mask6)

    scipy.misc.imsave("final_mask.png",final_mask)

    return(final_mask)


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

#
# Given a tiffile input, create outfile, filling
# in all water areas with the maskval.  
# Reproject from UTM into GCS and back if necessary.
#
def apply_wb_mask(tiffile,outfile,maskval=0):

    logging.info("Using mask value of {}".format(maskval))
    (x,y,trans,proj_in,data) = saa.read_gdal_file(saa.open_gdal_file(tiffile))    

    ptr = proj_in.find("UTM zone ")
    if ptr != -1:
        # tiffile in utm coordinates
        gcsfile = "tmp_gcs_{}.tif".format(os.getpid())
        tmpfile = "tmp_utm_{}.tif".format(os.getpid())
        
	# reproject into GCS coordinates
        logging.info("Reprojecting in GCS coordinates")
	gdal.Warp(gcsfile,tiffile,dstSRS="EPSG:4326",resampleAlg=GRIORA_Cubic)
        (x,y,trans,proj,data) = saa.read_gdal_file(saa.open_gdal_file(gcsfile))

        res = trans[1]
        xmin,ymax,xmax,ymin = getCorners(gcsfile)

    else:
        # tiffile is already in GCS coordinates
        res = trans[1]
	xmin,ymax,xmax,ymin = getCorners(tiffile)
        proj = proj_in

    # Get the mask array
    logging.info("Applying water body mask")
    mask_arr = create_wb_mask_file(xmin,ymin,xmax,ymax,res)
	
    # Apply the mask to the data
    data[mask_arr==0] = maskval
    saa.write_gdal_file_float(outfile,trans,proj,data,nodata=maskval)

    if ptr != -1:

        # Reproject back into UTM
        logging.info("Reprojecting back into UTM coordiantes")
        gdal.Warp(tmpfile,outfile,dstSRS=proj_in,dstNodata=maskval)
        shutil.move(tmpfile,outfile)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog='make_wb_mask_file.py',
      description='Create a water body mask wherein all water is 0 and land is 1')
    parser.add_argument('tiffile',help='Name of tif file to mask')
    parser.add_argument('outfile',help='Name of output masked file')
    parser.add_argument('-m','--maskval',help='Mask value to apply; default 0',type=float,default=0)
    args = parser.parse_args()

    logFile = "apply_wb_mask_{}_log.txt".format(os.getpid())
    logging.basicConfig(filename=logFile,format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',level=logging.DEBUG)
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.info("Starting run")

    apply_wb_mask(args.tiffile,args.outfile,maskval=args.maskval)
