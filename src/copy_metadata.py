#!/usr/bin/python

import os
import argparse
import saa_func_lib as saa
import shutil
from osgeo import gdal

def copy_metadata(infile, outfile):
    ds = saa.open_gdal_file(infile)
    md = ds.GetMetadata()
    print md

#    ds = saa.open_gdal_file(outfile)
#    ds.SetMetadata(md)

    outfile2 = "tmp_outfile.tif"
#    gdal.Translate(outfile2,outfile, metadataOptions = md)
#    shutil.move(outfile2,outfile)


    ds = saa.open_gdal_file(outfile)
    for item in md:
        ds1 = gdal.Translate('',ds,format='MEM',metadataOptions = ['{}={}'.format(item,md[item])])
        ds = ds1
    gdal.Translate(outfile,ds1)
 

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="copy_metadata.py",description="Copy metadata from one tif to another")
    parser.add_argument("infile",help="Input tif filename")
    parser.add_argument("outfile",help="Output tif filename")
    args = parser.parse_args()

    copy_metadata(args.infile, args.outfile)
