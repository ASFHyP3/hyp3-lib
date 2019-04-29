#!/usr/bin/python

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from asf_time_series import *


def raster_boundary2shape(inFile, threshold, outShapeFile):

  # Extract raster image metadata
  print('Extracting raster information ...')
  (fields, values, spatialRef) = raster_metadata(inFile)
  if spatialRef.GetAttrValue('AUTHORITY', 0) == 'EPSG':
    epsg = int(spatialRef.GetAttrValue('AUTHORITY', 1))

  # Generate GeoTIFF boundary geometry
  print('Extracting boundary geometry ...')
  (data, colFirst, rowFirst, geoTrans, proj) = \
    geotiff2boundary_mask(inFile, epsg, threshold)
  (rows, cols) = data.shape
  values[0]['originX'] = geoTrans[0]
  values[0]['originY'] = geoTrans[3]
  values[0]['rows'] = rows
  values[0]['cols'] = cols

  # Write broundary to shapefile
  print('Writing boundary to shapefile ...')
  data_geometry2shape(data, fields, values, spatialRef, geoTrans, outShapeFile)


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='raster_boundary2shape',
    description='generates boundary shapefile from GeoTIFF file',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('input', metavar='<geotiff file>',
    help='name of the GeoTIFF file')
  parser.add_argument('-threshold', metavar='<code>', action='store',
    default=None, help='threshold value what is considered blackfill')
  parser.add_argument('shape', metavar='<shape file>',
    help='name of the shapefile')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.input):
    print('GeoTIFF file (%s) does not exist!' % args.input)
    sys.exit(1)

  raster_boundary2shape(args.input, args.threshold, args.shape)
