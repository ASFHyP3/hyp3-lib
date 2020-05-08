"""Create a water body mask wherein all water is 0 and land is 1"""

from __future__ import print_function, absolute_import, division, unicode_literals

import os
# import numpy as np
import scipy.misc
import argparse
import logging
from osgeo import gdal
from hyp3lib.create_wb_mask import create_wb_mask
from hyp3lib import saa_func_lib as saa

import hyp3lib.etc


def create_wb_mask_file(xmin,ymin,xmax,ymax,res,gcs=True):

    cfgdir =os.path.abspath(os.path.join(os.path.dirname(hyp3lib.etc.__file__), "config"))
    myfile = os.path.join(cfgdir,"shapefile_dir.txt")
    f = open(myfile,"r")
    for line in f.readlines():
        cfgdir = line.strip()

    if gcs:

        shpfile = "{}/GSHHG_shp/f/GSHHS_f_L1.shp".format(cfgdir)
        mask1 = create_wb_mask(shpfile,xmin,ymin,xmax,ymax,res,outFile="mask1.png")

#        shpfile = "{}/GSHHG_shp/f/GSHHS_f_L2.shp".format(cfgdir)
#        mask2 = create_wb_mask(shpfile,xmin,ymin,xmax,ymax,res,outFile="mask2.png")
#        shpfile = "{}/GSHHG_shp/f/GSHHS_f_L3.shp".format(cfgdir)
#        mask3 = create_wb_mask(shpfile,xmin,ymin,xmax,ymax,res,outFile="mask3.png")
#        shpfile = "{}/GSHHG_shp/f/GSHHS_f_L4.shp".format(cfgdir)
#        mask4 = create_wb_mask(shpfile,xmin,ymin,xmax,ymax,res,outFile="mask4.png")
#
#        mask2 = np.logical_not(mask2)
#        mask3 = np.logical_not(mask3)
#        mask4 = np.logical_not(mask4)
#
#        final_mask = np.logical_and(mask1,mask2)
#        final_mask = np.logical_and(final_mask,mask3)
#        final_mask = np.logical_and(final_mask,mask4)

        final_mask = mask1
        scipy.misc.imsave("final_mask.png",final_mask)

    else:
        if ymin > 0:
            mask_file = "{}/WB_MASKS/Antimeridian_UTM1N_WaterMask1.tif".format(cfgdir)
        else:
            mask_file = "{}/WB_MASKS/Antimeridian_UTM1S_WaterMask1.tif".format(cfgdir)
        tmpfile = "water_mask.tif"

        coords = [xmin,ymax,xmax,ymin]
        gdal.Translate(tmpfile,mask_file,projWin=coords,xRes=res,yRes=res)
        x,y,trans,proj,data = saa.read_gdal_file(saa.open_gdal_file(tmpfile))
        final_mask = data
        # os.remove(tmpfile)

    return(final_mask)


def apply_wb_mask(tiffile,outfile,maskval=0,gcs=True):
    """
    Given a tiffile input, create outfile, filling in all water areas with the
    maskval.
    """

    logging.info("Using mask value of {}".format(maskval))
    (x,y,trans,proj,data) = saa.read_gdal_file(saa.open_gdal_file(tiffile))    

    res = trans[1]
    xmin,xmax,ymin,ymax = saa.getCorners(tiffile)

    # Get the mask array
    logging.info("Applying water body mask")
    mask_arr = create_wb_mask_file(xmin,ymin,xmax,ymax,res,gcs=gcs)
    
    saa.write_gdal_file_byte("final_mask.tif",trans,proj,mask_arr)
    
    # Apply the mask to the data
    data[mask_arr==0] = maskval
    saa.write_gdal_file_float(outfile,trans,proj,data,nodata=maskval)


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
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


if __name__ == '__main__':
    main()
