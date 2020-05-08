from __future__ import print_function, absolute_import, division, unicode_literals

import os
import logging
from osgeo import gdal
from osgeo import ogr
import scipy.misc

def create_wb_mask(shpfile,xmin,ymin,xmax,ymax,res,outFile=None,mask=1,gcs=True):
    
    if not os.path.isfile(shpfile):
        logging.error("ERROR: Can't find shapefile {}".format(shpfile))
        exit(1)

    src_ds = ogr.Open(shpfile)
    src_lyr=src_ds.GetLayer()

    logging.info("Using xmin, xmax {} {}, ymin, ymax {} {}".format(xmin,xmax,ymin,ymax))

    ncols = int((xmax-xmin)/res+0.5)
    nrows = int((ymax-ymin)/res+0.5)

    logging.info("Creating water body mask of size {} x {} (lxs) using {}".format(nrows,ncols,shpfile))
    maskvalue = mask 

    geotransform=(xmin,res,0,ymax,0,-res)  
    dst_ds = gdal.GetDriverByName('MEM').Create('', ncols, nrows, 1 ,gdal.GDT_Byte)
    dst_rb = dst_ds.GetRasterBand(1)
    dst_rb.Fill(0)
    dst_rb.SetNoDataValue(0)
    dst_ds.SetGeoTransform(geotransform)

    _ = gdal.RasterizeLayer(dst_ds, [maskvalue], src_lyr)
    dst_ds.FlushCache()
    mask_arr=dst_ds.GetRasterBand(1).ReadAsArray()

    if outFile is not None:
        scipy.misc.imsave(outFile,mask_arr)  

    return(mask_arr)

