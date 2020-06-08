"""Subsets a GeoTIFF file using an AOI from a shapefile"""

import argparse
import os
import shutil

import numpy as np
from osgeo import gdal, ogr, osr


def point_within_polygon(x, y, polygon):

  ring = polygon.GetGeometryRef(0)
  nPoints = ring.GetPointCount()
  inside = False

  if nPoints>0:
    p1x, p1y, p1z = ring.GetPoint(0)
    for i in range(nPoints + 1):
      p2x, p2y, p2z = ring.GetPoint(i % nPoints)
      if y > min(p1y, p2y):
        if y <= max(p1y, p2y):
          if x <= max(p1x, p2x):
            if p1y != p2y:
              xInt = (y - p1y)*(p2x - p1x)/(p2y -p1y) + p1x
            if p1x == p2x or x < xInt:
              inside = not inside
      p1x, p1y = p2x, p2y

  return inside


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
  if intersection is None or intersection.GetGeometryCount() == 0:
    print('Image does not intersect with vector AOI')
    shutil.copy(inGeoTIFF,outGeoTIFF)
    return

  envelope = intersection.GetEnvelope()
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
  numBands = inRaster.RasterCount
  outRaster = driver.Create(outGeoTIFF, cols, rows, numBands, dataType,
    ['COMPRESS=LZW'])
  outRaster.SetGeoTransform((originX, pixelWidth, 0, originY, 0, pixelHeight))
  outRasterSRS = osr.SpatialReference()
  outRasterSRS.ImportFromWkt(inRaster.GetProjectionRef())
  outRaster.SetProjection(outRasterSRS.ExportToWkt())
  for i in range(numBands):
    noDataValueActual = inRaster.GetRasterBand(i+1).GetNoDataValue()
    noDataValue = noDataValueActual
    if noDataValueActual is None: noDataValue = 0
    inRasterData = np.array(inRaster.GetRasterBand(i+1).ReadAsArray())
    outRasterData = inRasterData[startY:endY, startX:endX]
    for y in range(rows):
      for x in range(cols):
        pointX = originX + x*pixelWidth
        pointY = originY + y*pixelHeight
        if not point_within_polygon(pointX, pointY, intersection):
          outRasterData[y, x] = noDataValue
    outBand = outRaster.GetRasterBand(i+1)
    if noDataValueActual is not None:
        outBand.SetNoDataValue(noDataValue)
    outBand.WriteArray(outRasterData)
  outBand.FlushCache()


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('inGeoTIFF', help='name of the full size GeoTIFF file (input)')
    parser.add_argument('shapeFile', help='name of the shapefile (input)')
    parser.add_argument('outGeoTIFF', help='name of the subsetted GeoTIFF file (output)')
    args = parser.parse_args()

    if not os.path.exists(args.inGeoTIFF):
        parser.error(f'GeoTIFF file {args.inGeoTIFF} does not exist!')

    if not os.path.exists(args.shapeFile):
        parser.error(f'Shapefile {args.shapeFile} does not exist!')

    subset_geotiff_shape(args.inGeoTIFF, args.shapeFile, args.outGeoTIFF)


if __name__ == '__main__':
    main()

