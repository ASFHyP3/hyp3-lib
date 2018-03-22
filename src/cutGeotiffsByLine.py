#!/usr/bin/python

import argparse
from osgeo import gdal
import saa_func_lib as saa
import numpy as np

def getOrigins(files):

    ul = np.zeros((2,len(files)))
    lr = np.zeros((2,len(files)))

    for i in range(len(files)):
        x,y,trans,proj = saa.read_gdal_file_geo(saa.open_gdal_file(files[i]))
        ul[0,i] = trans[0]
        lr[0,i] = trans[0] + x*trans[1]
        ul[1,i] = trans[3]
        lr[1,i] = trans[3] + y*trans[5]

    return ul,lr,trans[1],trans[5]

def cutGeotiffsByLine(files):

    ul,lr,xres,yres = getOrigins(files)

    diff_ul = np.zeros((2,len(files)),dtype=np.uint16)
    diff_lr = np.zeros((2,len(files)),dtype=np.uint16)
     
    diff_ul[0] = (max(ul[0])-ul[0])/xres    
    diff_ul[1] = (min(ul[1])-ul[1])/yres
 
    print "Difference lists:"
    print diff_ul

    lrx = min(lr[0])
    lry = max(lr[1])
    lenx = (lrx-max(ul[0])) / xres
    leny = (lry-min(ul[1])) / yres

    print "Size of output images {} x {}".format(lenx,leny)

    outfiles = []   
    for i in range(len(files)):
        outfile = files[i].replace(".tif","_cut.tif")
        gdal.Translate(outfile,files[i],srcWin=[diff_ul[0,i],diff_ul[1,i],lenx,leny])
        outfiles.append(outfile)

    return(outfiles)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Clip a bunch of geotiffs to the same area.")
    parser.add_argument("infiles",nargs='+',help="Geotiff files to clip; output will be have _clip appended to the file name")
    args = parser.parse_args()
    cutGeotiffsByLine(args.infiles)
    
 
