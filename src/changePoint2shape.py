#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
import time as ti
from asf_time_series import *


def changePoint2shape(confidenceLevel, changeTime, timeFile, threshold,
  size, shapeFile):

  ### Read confidence level result and change time
  (confidence, geoTrans, proj, epsg, dtype, noData) = \
    geotiff2data(confidenceLevel)
  originX = geoTrans[0]
  originY = geoTrans[3]
  pixelSize = geoTrans[1]
  (change, geoTrans, proj, epsg, dtype, noData) = geotiff2data(changeTime)

  ### Read timestamp file
  timestamp = [line.rstrip('\n') for line in open(timeFile)]

  ### Determine confidence level mask
  mask = np.zeros_like(confidence, dtype=np.uint8)
  mask = np.where(confidence >= threshold, 1, 0).astype(np.uint8)
  kernelSize = (5,5)
  mask = ndimage.binary_opening(mask,
    structure=np.ones(kernelSize)).astype(np.uint8)
  data2geotiff(mask, geoTrans, proj, 'BYTE', 0, 'mask.tif')
  fields = []
  values = []
  data_geometry2shape(mask, fields, values, proj, geoTrans, 'mask.shp')
  mask = mask.astype(np.float32)
  mask[mask==0] = np.nan

  ### Extract area sizes and geometry
  (fields, proj, extent, features) = vector_meta('mask.shp')
  areaSize = []
  for ii in range(len(features)):
    areaSize.append(float(features[ii]['area']))
  areaCount = len(areaSize)
  index = np.argsort(areaSize)[::-1][:areaCount]

  ### Setup attributes
  fields = []
  field = {}
  field['name'] = 'confMean'
  field['type'] = ogr.OFTReal
  fields.append(field)
  field = {}
  field['name'] = 'confStd'
  field['type'] = ogr.OFTReal
  fields.append(field)
  field = {}
  field['name'] = 'change'
  field['type'] = ogr.OFTString
  field['width'] = 30
  fields.append(field)
  field = {}
  field['name'] = 'area'
  field['type'] = ogr.OFTReal
  fields.append(field)
  field = {}
  field['name'] = 'centroid'
  field['type'] = ogr.OFTString
  field['width'] = 50
  fields.append(field)

  ### Apply mask to confidence level and to change time
  confidenceMask = confidence*mask
  changeMask = change*mask

  ### Loop through polygons
  values = []
  for ii in range(areaCount):
    if areaSize[index[ii]] >= size:
      value = {}
      feature = features[index[ii]]
      value['area'] = feature['area']
      centroid = ogr.CreateGeometryFromWkt(feature['centroid'])
      centroidX = np.rint(centroid.GetX()/pixelSize)*pixelSize
      centroidY = np.rint(centroid.GetY()/pixelSize)*pixelSize
      centroid = ogr.Geometry(ogr.wkbPoint)
      centroid.AddPoint_2D(centroidX, centroidY)
      value['centroid'] = centroid.ExportToWkt()
      geometry = ogr.CreateGeometryFromWkt(feature['geometry'])
      value['geometry'] = geometry
      (minX, maxX, minY, maxY) = geometry.GetEnvelope()
      rows = int((maxY - minY)/pixelSize)
      cols = int((maxX - minX)/pixelSize)
      offX = int((minX - originX)/pixelSize)
      offY = int((maxY - originY)/pixelSize)
      subsetConfidence = confidenceMask[offY:rows+offY,offX:cols+offX]
      value['confMean'] = np.nanmean(subsetConfidence)
      value['confStd'] = np.nanstd(subsetConfidence)
      subsetChange = changeMask[offY:rows+offY,offX:cols+offX]
      value['change'] = timestamp[int(np.nanmedian(subsetChange))]
      values.append(value)

  ### Save results to shapefile
  geometry2shape(fields, values, proj, False, shapeFile)


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='changePoint2shape',
    description='converts change point analysis results to a shapefile',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('confidenceLevel', metavar='<confidence level file>',
    help='name of the change point analysis result: confidence level')
  parser.add_argument('changeTime', metavar='<change time file>',
    help='name of the change point analysis result: change time')
  parser.add_argument('timeFile', metavar='<time file',
    help='name of the file containing the time stamps')
  parser.add_argument('threshold', metavar='<threshold>',
    help='confidence level threshold to define change')
  parser.add_argument('areaSize', metavar='<areaSize>',
    help='minimum area size that constitues change')
  parser.add_argument('outFile', metavar='<shapefile>',
    help='name of the change point analysis shapefile')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.confidenceLevel):
    print('Change point analysis confidence level file (%s) does not exist!'\
      % args.confidenceLevel)
    sys.exit(1)
  if not os.path.exists(args.changeTime):
    print('Change point analysis change time file (%s) does not exist!' % \
      args.confidenceLevel)
    sys.exit(1)

  changePoint2shape(args.confidenceLevel, args.changeTime, args.timeFile,
    float(args.threshold), float(args.areaSize), args.outFile)
