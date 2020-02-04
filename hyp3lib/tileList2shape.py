#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from osgeo import ogr, osr
from hyp3lib.asf_geometry import geotiff2polygon, geometry2shape


def tileList2shape(listFile, shapeFile):

  # Set up shapefile attributes
  fields = []
  field = {}
  values = []
  field['name'] = 'tile'
  field['type'] = ogr.OFTString
  field['width'] = 100
  fields.append(field)

  files = [line.strip() for line in open(listFile)]
  for fileName in files:
    print('Reading %s ...' % fileName)
    polygon = geotiff2polygon(fileName)
    tile = os.path.splitext(os.path.basename(fileName))[0]
    value = {}
    value['tile'] = tile
    value['geometry'] = polygon
    values.append(value)
  spatialRef = osr.SpatialReference()
  spatialRef.ImportFromEPSG(4326)

  # Write geometry to shapefiles
  geometry2shape(fields, values, spatialRef, False, shapeFile)


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='tileList2shape',
    description='generates a shapefile from a list of tile files',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('input', metavar='<file list>',
    help='name of the tiles file list')
  parser.add_argument('shape', metavar='<shape file>',
    help='name of the shapefile')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.input):
    print('GeoTIFF file (%s) does not exist!' % args.input)
    sys.exit(1)

  tileList2shape(args.input, args.shape)
