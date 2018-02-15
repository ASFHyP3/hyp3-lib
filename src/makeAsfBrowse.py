#!/usr/bin/python

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from resample_geotiff import resample_geotiff

def makeAsfBrowse(geotiff, baseName):
    kmzName = baseName + ".kmz"
    pngName = baseName + ".png"
    lrgName = baseName + "_large.png"
    resample_geotiff(geotiff,2048,"KML",kmzName)
    resample_geotiff(geotiff,1024,"PNG",pngName)
    resample_geotiff(geotiff,2048,"PNG",lrgName)

if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='makeAsfBrowse',
    description='Resamples a GeoTIFF file and saves it in a number of formats',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('geotiff', help='name of GeoTIFF file (input)')
  parser.add_argument('basename', help='base name of output file (output)')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.geotiff):
    print('GeoTIFF file (%s) does not exist!' % args.geotiff)
    sys.exit(1)
  if len(os.path.splitext(args.basename)[1]) != 0:
    print('Output file (%s) has an extension!' % args.basename)
    sys.exit(1)

  makeAsfBrowse(args.geotiff, args.basename)
