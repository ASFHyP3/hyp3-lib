#!/usr/bin/python

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from asf_time_series import *


def raster2shape(inFile, classFile, threshold, background, outShapeFile):

  # Extract raster image metadata
  print('Extracting raster information ...')
  (fields, values, spatialRef) = raster_metadata(inFile)
  if spatialRef.GetAttrValue('AUTHORITY', 0) == 'EPSG':
    epsg = int(spatialRef.GetAttrValue('AUTHORITY', 1))

  # Read actual data
  (data, geoTrans, proj, epsg, dtype, noData) = geotiff2data(inFile)
  (rows, cols) = data.shape
  values[0]['originX'] = geoTrans[0]
  values[0]['originY'] = geoTrans[3]
  values[0]['rows'] = rows
  values[0]['cols'] = cols

  # Read classes from file
  classes = []
  with open(classFile) as csvFile:
    csvReader = csv.DictReader(csvFile)
    for row in csvReader:
      line = {}
      line['class'] = row['class']
      line['minimum'] = float(row['min'])
      if row['max'] == 'inf':
        line['maximum'] = np.inf
      else:
        line['maximum'] = float(row['max'])
      classes.append(line)

  # Write broundary to shapefile
  print('Writing classification to shapefile ...')
  data_geometry2shape_ext(data, fields, values, spatialRef, geoTrans, classes,
    threshold, background, outShapeFile)


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='raster2shape',
    description='converts a classification from raster to vector format',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('input', metavar='<geotiff file>',
    help='name of the GeoTIFF file')
  parser.add_argument('-classes', metavar='<thresholds>', default=None,
    help='CSV text files that classes based on area sizes')
  parser.add_argument('-threshold', metavar='<area>', action='store',
    default=None, help='threshold value what minium polygon area needs to be' \
    ' in m2')
  parser.add_argument('-background', metavar='<class>', action='store',
    default=None, help='removes background value from resulting polygon (zero'\
    ' is removed by default)')
  parser.add_argument('shape', metavar='<shape file>',
    help='name of the shapefile')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.input):
    print('GeoTIFF file (%s) does not exist!' % args.input)
    sys.exit(1)

  raster2shape(args.input, args.classes, args.threshold, args.background,
    args.shape)
