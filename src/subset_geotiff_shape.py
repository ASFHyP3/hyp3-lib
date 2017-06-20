#!/usr/bin/python

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
import datetime
import logging
import numpy as np
from osgeo import gdal, ogr, osr


def subset_geotiff_shape(inGeoTIFF, shapeFile, outGeoTIFF):
  
  print('Subsetting GeoTIFF file (%s) using an AOI from a shapefile (%s)' %
    (inGeoTIFF, shapeFile))
  
  # Suppress GDAL warnings
  gdal.UseExceptions()
  gdal.PushErrorHandler('CPLQuietErrorHandler')

  # Read input GeoTIFF parameters and generate boundary polygon
  inRaster = gdal.Open(inGeoTIFF)
  gt = inRaster.GetGeoTransform()
  originX = gt[0]
  originY = gt[3]
  pixelWidth = gt[1]
  pixelHeight = gt[5]
  cols = inRaster.RasterXSize
  rows = inRaster.RasterYSize
  dataType = inRaster.GetRasterBand(1).DataType
  rasterProj = inRaster.GetProjection()
  rasterSpatialRef = osr.SpatialReference(wkt = rasterProj)
  ulX = originX
  ulY = originY
  urX = originX + gt[1]*cols
  urY = originY 
  lrX = originX + gt[1]*cols + gt[2]*rows
  lrY = originY + gt[4]*cols + gt[5]*rows
  llX = originX
  llY = originY + gt[4]*cols + gt[5]*rows
  geometry = ('MULTIPOLYGON ((( %f %f, %f %f, %f %f, %f %f, %f %f )))' %
    (ulX, ulY, urX, urY, lrX, lrY, llX, llY, ulX, ulY))
  rasterPolygon = ogr.CreateGeometryFromWkt(geometry)

  # Extract boundary from shapefile and reproject polygon if necessary
  driver = ogr.GetDriverByName('ESRI Shapefile')
  shape = driver.Open(shapeFile, 0)
  vectorMultipolygon = ogr.Geometry(ogr.wkbMultiPolygon)
  layer = shape.GetLayer()
  vectorSpatialRef = layer.GetSpatialRef()
  if vectorSpatialRef != rasterSpatialRef:
    print('Need to re-project vector polygon')
    coordTrans = osr.CoordinateTransformation(vectorSpatialRef, rasterSpatialRef)
  for feature in layer:
    geometry = feature.GetGeometryRef()
    count = geometry.GetGeometryCount()
    if geometry.GetGeometryName() == 'MULTIPOLYGON':
      for i in range(count):
        polygon = geometry.GetGeometryRef(i)
        if vectorSpatialRef != rasterSpatialRef:
          polygon.Transform(coordTrans)
        vectorMultipolygon.AddGeometry(polygon)
    else:
      if vectorSpatialRef != rasterSpatialRef:
        geometry.Transform(coordTrans)
      vectorMultipolygon.AddGeometry(geometry)
  shape.Destroy()
  
  # Intersect polygons and determine subset parameters
  intersection = rasterPolygon.Intersection(vectorMultipolygon)
  print intersection
  if intersection.GetGeometryCount() == 0:
    print('Image does not intersect with vector AOI')
    sys.exit(1)
  envelope = intersection.GetEnvelope()
  print('envelope: {0}'.format(envelope))
  minX = envelope[0]
  minY = envelope[2]
  maxX = envelope[1]
  maxY = envelope[3]
  startX = int((minX - originX) / pixelWidth)
  startY = int((maxY - originY) / pixelHeight)
  if startX < 0:
    startX = 0
  if startY < 0:
    startY = 0
  originX = minX
  originY = maxY
  cols = abs(int((maxX - minX) / pixelWidth))
  rows = abs(int((maxY - minY) / pixelHeight))
  endX = startX + cols
  endY = startY + rows

  # Write output GeoTIFF with subsetted image
  driver = gdal.GetDriverByName('GTiff')
  outRaster = driver.Create(outGeoTIFF, cols, rows, 1, dataType, ['COMPRESS=LZW'])
  outRaster.SetGeoTransform((originX, pixelWidth, 0, originY, 0, pixelHeight))
  outRasterSRS = osr.SpatialReference()
  outRasterSRS.ImportFromWkt(inRaster.GetProjectionRef())
  outRaster.SetProjection(outRasterSRS.ExportToWkt())
  numBands = inRaster.RasterCount
  pt = ogr.Geometry(ogr.wkbPoint)
  pt.AssignSpatialReference(outRasterSRS)
  for i in range(numBands):
    noDataValue = inRaster.GetRasterBand(i+1).GetNoDataValue()
    inRasterData = np.array(inRaster.GetRasterBand(i+1).ReadAsArray())
    outRasterData = inRasterData[startY:endY, startX:endX]
    outBand = outRaster.GetRasterBand(i+1)
    if noDataValue is not None:
        outBand.SetNoDataValue(noDataValue)
    outBand.WriteArray(outRasterData)
  outBand.FlushCache()


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='subset_geotiff_shape',
    description='Subsets a GeoTIFF file using an AOI from a shapefile',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('inGeoTIFF', help='name of the full size GeoTIFF file (input)')
  parser.add_argument('shapeFile', help='name of the shapefile (input)')
  parser.add_argument('outGeoTIFF', help='name of the subsetted GeoTIFF file (output)')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.inGeoTIFF):
    print('GeoTIFF file (%s) does not exist!' % args.inGeoTIFF)
    sys.exit(1)

  if not os.path.exists(args.shapeFile):
    print('Shapefile (%s) does not exist!' % args.shapeFile)
    sys.exit(1)

  subset_geotiff_shape(args.inGeoTIFF, args.shapeFile, args.outGeoTIFF)
