"""Clip a bunch of geotiffs to the same area"""

from __future__ import print_function, absolute_import, division, unicode_literals

import argparse
import os
from osgeo import gdal
from hyp3lib import saa_func_lib as saa
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


def copyOrigins(files,all_coords,all_pixsize):
    
    ul = np.zeros((2,len(files)))
    lr = np.zeros((2,len(files)))

    for i in range(len(files)):
        coords = all_coords[i]
        ul[0,i] = coords[0]
        lr[0,i] = coords[2]
        ul[1,i] = coords[1]
        lr[1,i] = coords[3]
 
        if i == 0:
            xres = all_pixsize[i]
            yres = all_pixsize[i]

    return ul,lr,xres,yres


def cutGeotiffsByLine(files,all_coords=None,all_pixsize=None):

    if all_coords is None:
        ul,lr,xres,yres = getOrigins(files)
    else:
        ul,lr,xres,yres = copyOrigins(files,all_coords,all_pixsize)

    diff_ul = np.zeros((2,len(files)))

    diff_ul[0] = (max(ul[0])-ul[0])/xres    
    diff_ul[1] = -1*(min(ul[1])-ul[1])/(-1*yres)

    print("Difference list:")
    print(diff_ul)

    lrx = min(lr[0])
    lry = max(lr[1])
    lenx = (lrx-max(ul[0])) / xres
    leny = -1*(lry-min(ul[1])) / (-1*yres)
    if leny < 0:
        leny = abs(leny)
        diff_ul[1] = diff_ul[1] * -1
    print("Size of output images {} x {}".format(lenx, leny))

    outfiles = []   
    for i in range(len(files)):
        outfile = files[i].replace(".tif","_cut.tif")
        if all_coords is not None:
            outfile = os.path.basename(outfile)
        print("Processing file {} to create file {}".format(files[i], outfile))
        gdal.Translate(outfile,files[i],srcWin=[diff_ul[0,i],diff_ul[1,i],lenx,leny],noData=0)
        outfiles.append(outfile)

    return(outfiles)


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument("infiles", nargs='+',
                        help="Geotiff files to clip; output will be have _clip appended to the file name")
    args = parser.parse_args()

    cutGeotiffsByLine(args.infiles)


if __name__ == "__main__":
    main()
