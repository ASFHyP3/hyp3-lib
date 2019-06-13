#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from asf_geometry import *


def point2aoi(lat, lon, rows, cols, pixelSize):

  ### Transform geographic center to native UTM coordinates
  utmZone = int((lon + 180.0)/6.0 + 1.0)
  epsg = (32600 + utmZone) if lat > 0 else (32700 + utmZone)
  centerPoint = ogr.Geometry(ogr.wkbPoint)
  centerPoint.AddPoint_2D(lon, lat)
  inSpatialRef = osr.SpatialReference()
  inSpatialRef.ImportFromEPSG(4326)
  outSpatialRef = osr.SpatialReference()
  outSpatialRef.ImportFromEPSG(epsg)
  coordTrans = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)
  centerPoint.Transform(coordTrans)

  ### Force coordinates on the grid
  centerX = np.rint(centerPoint.GetX()/pixelSize)*pixelSize
  centerY = np.rint(centerPoint.GetY()/pixelSize)*pixelSize

  ### Determine the corners of AOI mask
  originX = centerX - cols*pixelSize/2
  originY = centerY + rows*pixelSize/2
  polygon = ogr.Geometry(ogr.wkbPolygon)
  ring = ogr.Geometry(ogr.wkbLinearRing)
  ring.AddPoint_2D(originX, originY)
  ring.AddPoint_2D(originX + cols*pixelSize, originY)
  ring.AddPoint_2D(originX + cols*pixelSize, originY - rows*pixelSize)
  ring.AddPoint_2D(originX, originY - rows*pixelSize)
  ring.AddPoint_2D(originX, originY)
  polygon.AddGeometry(ring)
  ring = None

  return polygon.ExportToWkt()


def point2aoiShape(lat, lon, rows, cols, pixelSize, outFile):

  ### Generate AOI polygon
  print('Generating AOI polygon ...')
  polygon = point2aoi(lat, lon, rows, cols, pixelSize)

  ### Prepare for writing to shapefile
  multiPolygon = ogr.Geometry(ogr.wkbMultiPolygon)
  multiPolygon.AddGeometry(ogr.CreateGeometryFromWkt(polygon))

  fields = []
  field = {}
  field['name'] = 'cenLat'
  field['type'] = ogr.OFTReal
  fields.append(field)
  field = {}
  field['name'] = 'cenLon'
  field['type'] = ogr.OFTReal
  fields.append(field)
  field = {}
  field['name'] = 'centerX'
  field['type'] = ogr.OFTReal
  fields.append(field)
  field = {}
  field['name'] = 'centerY'
  field['type'] = ogr.OFTReal
  fields.append(field)
  field = {}
  field['name'] = 'epsg'
  field['type'] = ogr.OFTInteger
  fields.append(field)
  field = {}
  field['name'] = 'pixSize'
  field['type'] = ogr.OFTReal
  fields.append(field)
  field = {}
  field['name'] = 'cols'
  field['type'] = ogr.OFTInteger
  fields.append(field)
  field = {}
  field['name'] = 'rows'
  field['type'] = ogr.OFTInteger
  fields.append(field)
  field = {}

  values = []
  value = {}
  value['cenLat'] = lat
  value['cenLon'] = lon
  centroid = ogr.CreateGeometryFromWkt(polygon).Centroid()
  value['centerX'] = centroid.GetX()
  value['centerY'] = centroid.GetY()
  utmZone = int((lon + 180.0)/6.0 + 1.0)
  value['epsg'] = (32600 + utmZone) if lat > 0 else (32700 + utmZone)
  proj = osr.SpatialReference()
  proj.ImportFromEPSG(value['epsg'])
  value['pixSize'] = pixelSize
  value['cols'] = cols
  value['rows'] = rows
  value['geometry'] = multiPolygon
  values.append(value)

  ### Save AOI to shapefile
  print('Saving areas of interest to shapefile ({0}) ...'.format(outFile))
  geometry2shape(fields, values, proj, False, outFile)


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='point2aoiShape',
    description='generates an area of interest mask shapefile',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('lat', metavar='<latitude>',
    help='center latitude of area of interest')
  parser.add_argument('lon', metavar='<longitude>',
    help='center longitude of area of interest')
  parser.add_argument('height', metavar='<AOI height>',
    help='height of area of interest')
  parser.add_argument('width', metavar='<AOI width>',
    help='width of area of interest')
  parser.add_argument('outFile', metavar='<output file>',
    help='name of the output shapefile')
  parser.add_argument('-pixelSize', metavar='<pixel size>', default=10.0,
    help='pixel size of the imagery (default = 10 m)')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  point2aoiShape(float(args.lat), float(args.lon), int(args.height), \
    int(args.width), args.pixelSize, args.outFile)
