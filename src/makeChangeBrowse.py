#!/usr/bin/python

import argparse
import saa_func_lib as saa
import numpy as np
import sys, os
from makeAsfBrowse import makeAsfBrowse
from osgeo import gdal

MAX_CLASSES = 10

def makeChangeBrowse(geotiff):

    # read in the data
    x,y,trans,proj,data = saa.read_gdal_file(saa.open_gdal_file(geotiff))

    #
    # get data median and histogram
    #
    median = np.median(data)
    bins = np.zeros(MAX_CLASSES,dtype=np.int8)
    for i in range(MAX_CLASSES):
        bins[i] = i
    hist = np.histogram(data,bins=bins)

    #
    # count the number of classes present in histogram and set class number, 
    # making the median class 0, keeping all zeors as class 0, and all others
    # with histogram values to a linear sequence 1, 2, 3, ...
    #
    class_cnt = 0
    next_class = 1
    classifications = np.zeros(MAX_CLASSES,dtype=np.int8)
    classifications[:] = -1
    classifications[0] = 0
    for i in range(0,len(hist[0])):
        if hist[0][i] != 0:
            class_cnt = class_cnt + 1
            if hist[1][i] == 0:
                # we have zeros in the image - need to be handled as background
                classifications[i] = 0
            elif i == median:
                classifications[i] = 0
            else:
                classifications[i] = next_class
                next_class = next_class + 1 

    #
    # Make LUT to map classifications to greyscale values
    # Start at 64, increment by 192/(#classes-2) to get
    # sequences like {64,255}, {64,160,255}, {64,128,192,256}, etc,
    # always leaving the median class and zero pixels as zero valued
    #
    lut = np.zeros(class_cnt,dtype=np.uint8)
    if class_cnt == 1:
        print "ERROR: Only found one class"
        exit(1)
    if (class_cnt == 2):
        lut[0] = 0
        lut[1] = 255
    else:
        val = 64
        inc = 192/(class_cnt-2)
        for i in range(class_cnt):
            if i != median and hist[1][i] != 0:
                lut[classifications[i]] =  int(val)
                val = val + inc
                if val > 255:
                    val = int(255)
  
    #
    # Use the look up table to set the values in newData array
    #
    newData = np.zeros(data.shape,dtype=np.uint8)
    newData = lut[classifications[data]]

    #
    # Write out the greyscale png files
    # 
    outName = geotiff.replace(".tif","_byte.tif")
    pngName = geotiff.replace(".tif","_byte.png")
    saa.write_gdal_file_float(outName,trans,proj,newData)
    gdal.Translate(pngName,outName,format="PNG",outputType=gdal.GDT_Byte,scaleParams=[[0,255]],noData="0 0 0")
    os.remove(outName)

    #
    # Create the color version of the data
    # Here, we use the same classifications as
    # an index into a color look up table.
    #
    red = np.zeros(data.shape,dtype=np.uint8)
    blue = np.zeros(data.shape,dtype=np.uint8)
    green = np.zeros(data.shape,dtype=np.uint8)

    red_lut  =  [0,255,  0,  0,255,255,  0,128,128,  0]
    green_lut = [0,  0,  0,255,128,  0,255,255,  0,128]
    blue_lut  = [0,  0,255,  0,  0,128,128,  0,255,255]

    for i in range(y):
        for j in range(x):    
                k = classifications[data[i,j]]
                red[i,j] = red_lut[k]
                blue[i,j] = blue_lut[k]
                green[i,j] = green_lut[k]

    #
    # Write out the RGB tif
    #
    outName = geotiff.replace(".tif","_rgb.tif")
    tmpName = geotiff.replace(".tif","_rgb")
    saa.write_gdal_file_rgb(outName,trans,proj,red,green,blue) 

    #
    # Make the ASF standard browse and kmz images
    # 
    makeAsfBrowse(outName,tmpName)
    os.remove(outName)

if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='MakeNiyiBrowse',
    description='Creates browse images for Niyi change detection geotiffs')
  parser.add_argument('geotiff', help='name of GeoTIFF file (input)')

  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.geotiff):
    print('ERROR: GeoTIFF file (%s) does not exist!' % args.geotiff)
    sys.exit(1)

  makeNiyiBrowse(args.geotiff)


