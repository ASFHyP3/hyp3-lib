#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from asf_time_series import *


def aoiShape(inFile, threshold, number, rows, cols, outBase):

  ### Extract information from SACD shapefile
  print('Extracting information from SACD shapefile ({0}) ...'.format(inFile))
  (fields, proj, extent, features) = vector_meta(inFile)

  ### Put area sizes into a list
  areaSize = []
  for ii in range(len(features)):
    areaSize.append(float(features[ii]['area']))
  areaCount = len(areaSize)
  index = np.argsort(areaSize)[::-1][:areaCount]

  ### Determine how many areas of interest we have when defining threshold
  if threshold > 0:
    suffix = ('threshold')
    for ii in range(areaCount):
      if areaSize[index[ii]] >= threshold:
        number = ii
    number += 1
  else:
    suffix = ('number')

  ### Go through features
  for ii in range(number):

    ## Force the center point on a grid
    centerPoint = ogr.CreateGeometryFromWkt(features[index[ii]]['centroid'])
    pixelSize = features[index[ii]]['pixSize']
    centerX = np.rint(centerPoint.GetX()/pixelSize)*pixelSize
    centerY = np.rint(centerPoint.GetY()/pixelSize)*pixelSize
    centerPoint = ogr.Geometry(ogr.wkbPoint)
    centerPoint.AddPoint_2D(centerX, centerY)
    features[index[ii]]['centroid'] = centerPoint.ExportToWkt()

    ## Determine the corners of AOI mask
    originX = centerX - cols*pixelSize/2
    originY = centerY + rows*pixelSize/2
    features[index[ii]]['originX'] = originX
    features[index[ii]]['originY'] = originY
    multiPolygon = ogr.Geometry(ogr.wkbMultiPolygon)
    polygon = ogr.Geometry(ogr.wkbPolygon)
    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint_2D(originX, originY)
    ring.AddPoint_2D(originX + cols*pixelSize, originY)
    ring.AddPoint_2D(originX + cols*pixelSize, originY - rows*pixelSize)
    ring.AddPoint_2D(originX, originY - rows*pixelSize)
    ring.AddPoint_2D(originX, originY)
    polygon.AddGeometry(ring)
    multiPolygon.AddGeometry(polygon)
    ring = None
    polygon = None
    features[index[ii]]['geometry'] = multiPolygon

    ## Save polygon in shapefile
    values = []
    values.append(features[index[ii]])
    outFile = ('%s_%s_%02d.shp' % (outBase, suffix, ii+1))
    print('Saving areas of interest to shapefile ({0})'.format(outFile))
    geometry2shape(fields, values, proj, False, outFile)


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='aoiShape',
    description='generates an area of interest mask shapefile',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('inFile', metavar='<SACD shapefile>',
    help='name of the SACD polygons shapefile')
  aoi = parser.add_mutually_exclusive_group(required=True)
  aoi.add_argument('-threshold', metavar='<min area>', action='store',
    default=-1.0, help='save areas larger than this threshold')
  aoi.add_argument('-number', metavar='<count>', action='store',
    default=-1, help='save a certain number of areas of interest')
  parser.add_argument('height', metavar='<AOI height>',
    help='height of AOI mask')
  parser.add_argument('width', metavar='<AOI width>',
    help='width of AOI mask')
  parser.add_argument('outFile', metavar='<output file>',
    help='basename of the output shapefiles')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.inFile):
    print('AOI shapefile (%s) does not exist!' % args.inFile)
    sys.exit(1)

  height = int(args.height)
  width = int(args.width)
  if height % 2 != 0:
    print('Height needs to be an even number of pixels!')
    sys.exit(1)
  if width % 2 != 0:
    print('Width needs to be an even number of pixels!')
    sys.exit(1)

  aoiShape(args.inFile, float(args.threshold), int(args.number), height, width,
    args.outFile)
