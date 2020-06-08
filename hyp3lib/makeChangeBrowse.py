"""Creates browse images for classified change detection geotiffs"""

import argparse
import os

import numpy as np
from osgeo import gdal

import hyp3lib.saa_func_lib as saa
from hyp3lib.makeAsfBrowse import makeAsfBrowse

MAX_CLASSES = 10


def makeChangeBrowse(geotiff,type="MSCD"):

    # read in the data
    x,y,trans,proj,data = saa.read_gdal_file(saa.open_gdal_file(geotiff))
   
    red = np.zeros(data.shape,dtype=np.uint8)
    blue = np.zeros(data.shape,dtype=np.uint8)
    green = np.zeros(data.shape,dtype=np.uint8)
    newData = np.zeros(data.shape,dtype=np.uint8)

    if type == "SACD": 

        #
        # Make the greyscale image
        #
        lut = [0,64,0,192]

        #
        # Make the color images
        #
        red_lut  =   [0,255,  0,  1]
        green_lut  = [0,  1,  0,  1]
        blue_lut =   [0,  1,  0,255]

        for i in range(y):
            for j in range(x):    
                newData[i,j] = lut[data[i,j]]
                red[i,j] = red_lut[data[i,j]]
                green[i,j] = green_lut[data[i,j]]
                blue[i,j] = blue_lut[data[i,j]] 

    else:        

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
            print("ERROR: Only found one class")
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
        newData = lut[classifications[data]]

        #
        # Create the color version of the data
        # Here, we use the same classifications as
        # an index into a color look up table.
        #
        red_lut  =  [1,255,  1,  1,255,255,  1,128,128,  1]
        green_lut = [1,  1,  1,255,128,  1,255,255,  1,128]
        blue_lut  = [1,  1,255,  1,  1,128,128,  1,255,255]

        for i in range(y):
            for j in range(x):    
                k = classifications[data[i,j]]
                red[i,j] = red_lut[k]
                blue[i,j] = blue_lut[k]
                green[i,j] = green_lut[k]

    #
    # Write out the greyscale png files
    # 
    outName = geotiff.replace(".tif","_byte.tif")
    pngName = geotiff.replace(".tif","_byte_full.png")
    saa.write_gdal_file_byte(outName,trans,proj,newData.astype(np.byte))
    gdal.Translate(pngName,outName,format="PNG",outputType=gdal.GDT_Byte,scaleParams=[[0,255]],noData="0 0 0")
    os.remove(outName)

    #
    # Write out the RGB tif
    #
    outName = geotiff.replace(".tif","_rgb.tif")
    pngName = geotiff.replace(".tif","_rgb_full.png")
    saa.write_gdal_file_rgb(outName,trans,proj,red,green,blue) 
    gdal.Translate(pngName,outName,format="PNG",outputType=gdal.GDT_Byte,scaleParams=[[0,255]],noData="0 0 0")

    #
    # Make the ASF standard browse and kmz images
    # 
    tmpName = geotiff.replace(".tif","_rgb")
    makeAsfBrowse(outName,tmpName,use_nn=True)
    os.remove(outName)


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('geotiff', help='name of GeoTIFF file (input)')
    parser.add_argument('type', help='type of input file (MSCD or SACD)')
    args = parser.parse_args()

    if not os.path.exists(args.geotiff):
        parser.error(f'GeoTIFF file {args.geotiff} does not exist!')

    makeChangeBrowse(args.geotiff, type=args.type)


if __name__ == '__main__':
    main()
