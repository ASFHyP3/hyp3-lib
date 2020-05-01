"""Convert a floating point tiff into a byte tiff using 2-sigma scaling."""

from __future__ import print_function, absolute_import, division, unicode_literals

import os
import argparse
from hyp3lib import saa_func_lib as saa
import numpy as np
from osgeo import gdal


def get2sigmacutoffs(fi):
    (x,y,trans,proj,data) = saa.read_gdal_file(saa.open_gdal_file(fi))
    data = data.astype(float)
    data[data==0]=np.nan
    top = np.nanpercentile(data,99)
    data[data>top]=top
    stddev = np.nanstd(data)
    mean = np.nanmean(data)
    lo = mean - 2*stddev
    hi = mean + 2*stddev
    return lo,hi


def byteSigmaScale(infile,outfile):
    lo,hi = get2sigmacutoffs(infile)
    print("2-sigma cutoffs are {} {}".format(lo, hi))
    gdal.Translate(outfile,infile,outputType=gdal.GDT_Byte,scaleParams=[[lo,hi,1,255]],resampleAlg="average",noData="0")

    # For some reason, I'm still getting zeros in my byte images eventhough I'm using 1,255 scaling!
    # The following in an attempt to fix that!
    (x,y,trans,proj,data) = saa.read_gdal_file(saa.open_gdal_file(infile))
    mask = (data>0).astype(bool)
    (x,y,trans,proj,data) = saa.read_gdal_file(saa.open_gdal_file(outfile))
    mask2 = (data>0).astype(bool)
    mask3 = mask ^ mask2
    data[mask3==True] = 1
    saa.write_gdal_file_byte(outfile,trans,proj,data,nodata=0) 


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument("infile", help="Geotiff file to convert")
    parser.add_argument("outfile", help="Name of output file to create")
    args = parser.parse_args()
    byteSigmaScale(args.infile, args.outfile)


if __name__ == "__main__":
    main()
