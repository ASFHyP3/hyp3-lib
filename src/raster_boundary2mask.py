#!/usr/bin/python

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from asf_time_series import *


def raster_boundary2mask(inFile, outFile):

  # Extract other raster image metadata
  print('Extracting raster image metadata ...')
  (outSpatialRef, outGt, outShape, outPixel) = raster_meta(inFile)
  if outSpatialRef.GetAttrValue('AUTHORITY', 0) == 'EPSG':
    epsg = int(outSpatialRef.GetAttrValue('AUTHORITY', 1))

  # Generate GeoTIFF boundary geometry
  print('Extracting boundary geometry ...')
  (data, colFirst, rowFirst, geoTrans, proj) = \
    geotiff2boundary_mask(inFile, epsg)

  # Write broundary to shapefile
  print('Writing boundary to mask file ...')
  data2geotiff(data, geoTrans, proj, 'BYTE', 0, outFile)


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='raster_boundary2mask',
    description='generates boundary mask file from GeoTIFF file',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('input', metavar='<geotiff file>',
    help='name of the GeoTIFF file')
  parser.add_argument('output', metavar='<mask file>',
    help='name of the mask file')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.input):
    print('GeoTIFF file (%s) does not exist!' % args.input)
    sys.exit(1)

  raster_boundary2mask(args.input, args.output)
