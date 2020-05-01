"""Apply enhanced lee filer to geotiff image"""

from __future__ import print_function, absolute_import, division, unicode_literals

from hyp3lib import saa_func_lib as saa
import numpy as np
import os
import argparse
from scipy.ndimage.filters import uniform_filter


def enh_lee(looks,size,dampening_factor,img):

    Cu = np.sqrt(1/looks)
    Cmax = np.sqrt(1+2/looks) 

    Im = uniform_filter(img, (size, size))
    diff = img - Im
    sqdiff = diff*diff
    mean_diff = uniform_filter(sqdiff, (size, size))
    mean_diff[mean_diff<0] = 0   

    S = np.sqrt(mean_diff)
    Ic = img

    mask = np.zeros(Im.shape,np.uint8)
    mask[Im==0] = 1
    Ci = S/Im
    Ci[mask] = 0

    W = np.exp(-1.0*dampening_factor*(Ci-Cu)/(Cmax-Ci))   
    W[np.isnan(W)]=0

    mask1 = np.zeros(Im.shape,np.uint8)
    mask1[Ci<=Cu] = 1
    T1 = Im * mask1

    mask2 = np.zeros(Im.shape,np.uint8)
    mask2[Ci>=Cmax] =  1
    T2 = Ic * mask2
 
    mask1 = np.logical_not(mask1)
    mask2 = np.logical_not(mask2)
    mask3 = np.logical_and(mask1,mask2)
    T3 = mask3 * (Im*W + Ic*(1-W))
 
    R = T1 + T2 + T3

    R[np.isnan(R)] = 0
    R[np.abs(R)<0.00001] = 0
 
    return(R)


def enhanced_lee(infile,outfile,looks,size,dampening):
    
     x,y,trans,proj,img = saa.read_gdal_file(saa.open_gdal_file(infile))
     img2 = enh_lee(looks,size,dampening,img)
     saa.write_gdal_file_float(outfile,trans,proj,img2)


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument("infile",help="Geotiff file to smooth")
    parser.add_argument("outfile",help="Output smoothed geotiff file")
    parser.add_argument("looks",help="Looks to use",type=float)
    parser.add_argument("size",help="Kernel size to use",type=float)
    parser.add_argument("dampening",help="Dampening factor",type=float)
    args = parser.parse_args()

    enhanced_lee(args.infile,args.outfile,args.looks,args.size,args.dampening)


if __name__ == "__main__":
    main()
