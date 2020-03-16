#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import sys
import os
from osgeo import gdal, ogr, osr
import numpy as np
from asf_geometry import geometry2shape, data2geotiff, reproject_extent
from asf_geometry import geotiff2data
from asf_time_series import vector_meta
from get_dem import get_dem


def get_mask(inFile, maskType, maskClass, maskThreshold, maskBuffer, outBase):

  ### Generate GeoTIFF version of mask
  (fields, proj, extent, features) = vector_meta(inFile)
  envelope = ogr.CreateGeometryFromWkt(features[0]['geometry']).GetEnvelope()
  (minX, maxX, minY, maxY) = envelope
  (maskMinX, maskMaxX, maskMinY, maskMaxY) = envelope
  maskProj = proj
  posting = features[0]['pixSize']
  epsg = int(proj.GetAttrValue('AUTHORITY', 1))
  if epsg != 4326:
    extent = reproject_extent(minX, maxX, minY, maxY, posting, epsg, 4326)
  (minX, maxX, minY, maxY) = extent
  print('Extracting mask - minX: %.5f, maxX: %.5f, minY: %.5f, maxY: %.5f' % \
    (minX, maxX, minY, maxY))
  maskGeoTIFF = ('%s.tif' % outBase)
  maskBlackfillGeoTIFF = ('%s_blackfill.tif' % outBase)
  maskName = get_dem(minX, minY, maxX, maxY, maskGeoTIFF, demName=maskType)

  ### Cut out the mask to initial outline
  print('Cutting out the mask to initial outline ...')
  result = gdal.Warp(maskBlackfillGeoTIFF, maskGeoTIFF, cutlineDSName=inFile,
    cropToCutline=True, xRes=posting, yRes=posting, targetAlignedPixels=True,
    creationOptions=['COMPRESS=LZW'])
  result = None

  ### Read raster mask file and convert to mask shapefile
  #### Read raster mask file back in
  outRaster = gdal.Open(maskBlackfillGeoTIFF)
  proj = osr.SpatialReference()
  proj.ImportFromWkt(outRaster.GetProjectionRef())
  geoTrans = outRaster.GetGeoTransform()
  outBand = outRaster.GetRasterBand(1)
  maskImage = outBand.ReadAsArray()
  (lineCount, sampleCount) = maskImage.shape
  maskBase = ('%s_%s' % (outBase, maskClass.lower()))

  #### VISNAV masks
  if maskType.upper() == 'VISNAV':

    ##### VISNAV classes
    if maskClass.upper() == 'WATER':
      print('Generating water mask for VISNAV mask ...')
      ## water value: 11
      maskImage[np.rint(maskImage)!=11] = 0.0
      maskImage[maskImage>0] = 1.0
      maskImage = maskImage.astype(np.uint8)
      maskFile = ('%s.tif' % maskBase)
      data2geotiff(maskImage, geoTrans, proj, 'BYTE', 0, maskFile)

  #### Define shapefile attributes
  fields = []
  field = {}
  field['name'] = 'ID'
  field['type'] = ogr.OFTInteger
  fields.append(field)

  #### Polygonize the raster image
  print('Polygonizing mask raster image ...')
  ogrDriver = ogr.GetDriverByName('Memory')

  ### Original version
  outVector = ogrDriver.CreateDataSource('out')
  outLayer = outVector.CreateLayer('mask', srs=proj)
  fieldDefinition = ogr.FieldDefn('ID', ogr.OFTInteger)
  outLayer.CreateField(fieldDefinition)
  values = []
  raster = gdal.Open(maskFile)
  maskBand = raster.GetRasterBand(1)
  gdal.Polygonize(maskBand, maskBand, outLayer, 0, [], None)
  polyCount = 0
  for outFeature in outLayer:
    geometry = outFeature.GetGeometryRef()
    multipolygon = ogr.Geometry(ogr.wkbMultiPolygon)
    multipolygon.AddGeometry(geometry)
    value = {}
    polyCount += 1
    value['ID'] = polyCount
    value['geometry'] = multipolygon
    values.append(value)
    multipolygon = None
    outFeature = None
  outLayer = None
  raster = None
  print('  Found {0} polygons in original mask file'.format(polyCount))

  #### Save to mask shapefile
  maskOriginalShape = maskBase + '_original.shp'
  print('Saving original mask polygons to shapefile ({0}) ...' \
    .format(os.path.basename(maskOriginalShape)))
  geometry2shape(fields, values, proj, False, maskOriginalShape)

  ### Thresholded version
  outVector = ogrDriver.CreateDataSource('out')
  outLayer = outVector.CreateLayer('mask', srs=proj)
  fieldDefinition = ogr.FieldDefn('ID', ogr.OFTInteger)
  outLayer.CreateField(fieldDefinition)
  values = []
  raster = gdal.Open(maskFile)
  maskBand = raster.GetRasterBand(1)
  gdal.Polygonize(maskBand, maskBand, outLayer, 0, [], None)
  polyCount = 0
  for outFeature in outLayer:
    geometry = outFeature.GetGeometryRef()
    geomArea = geometry.GetArea()
    if geomArea > maskThreshold:
      multipolygon = ogr.Geometry(ogr.wkbMultiPolygon)
      multipolygon.AddGeometry(geometry)
      value = {}
      polyCount += 1
      value['ID'] = polyCount
      value['geometry'] = multipolygon
      values.append(value)
      multipolygon = None
    outFeature = None
  outLayer = None
  raster = None
  print('  Found {0} polygons applying a threshold of {1}'.format(polyCount,
    maskThreshold))

  #### Save to mask shapefile
  maskThresholdShape = maskBase + '_threshold.shp'
  print('Saving thresholded mask polygons to shapefile ({0}) ...' \
    .format(os.path.basename(maskThresholdShape)))
  geometry2shape(fields, values, proj, False, maskThresholdShape)

  #### Save to buffered mask shapefile
  maskBufferShape = ('%s_buffer.shp' % maskBase)
  print('Saving buffered mask polygons to shapefile ({0}) ...' \
    .format(os.path.basename(maskBufferShape)))
  print('  Applying a buffer of {0} m'.format(maskBuffer))
  inVector = ogr.Open(maskThresholdShape)
  inLayer = inVector.GetLayer()
  spatialRef = inLayer.GetSpatialRef()
  shpDriver = ogr.GetDriverByName('ESRI Shapefile')
  outVector = shpDriver.CreateDataSource(maskBufferShape)
  outLayer = outVector.CreateLayer(maskBufferShape, geom_type=ogr.wkbPolygon,
    srs=spatialRef)
  featureDefinition = outLayer.GetLayerDefn()
  for feature in inLayer:
    inGeometry = feature.GetGeometryRef()
    outGeometry = inGeometry.Buffer(maskBuffer)
    outFeature = ogr.Feature(featureDefinition)
    outFeature.SetGeometry(outGeometry)
    outLayer.CreateFeature(outFeature)
    outFeature.Destroy()

  #### Read in vector metadata again
  cols = abs(int((maskMaxX - maskMinX)/posting))
  rows = abs(int((maskMaxY - maskMinY)/posting))

  #### Rasterize mask polygon
  maskBufferGeoTIFF = ('%s_buffer.tif' % maskBase)
  print('Saving buffered mask to raster file ({0}) ...' \
    .format(os.path.basename(maskBufferGeoTIFF)))
  gdalDriver = gdal.GetDriverByName('MEM')
  outRaster = gdalDriver.Create('', cols, rows, 1, gdal.GDT_Int16)
  outRaster.SetGeoTransform((maskMinX, posting, 0, maskMaxY, 0, -posting))
  outRaster.SetProjection(spatialRef.ExportToWkt())
  outBand = outRaster.GetRasterBand(1)
  outBand.SetNoDataValue(0)
  outBand.FlushCache()
  gdal.RasterizeLayer(outRaster, [1], outLayer, burn_values=[1])
  outRaster.FlushCache()
  mask = outRaster.GetRasterBand(1).ReadAsArray()
  outVector.Destroy()

  geoTrans = (maskMinX, posting, 0, maskMaxY, 0, -posting)
  data2geotiff(mask, geoTrans, spatialRef, 'INT16', 0, maskBufferGeoTIFF)


if __name__ == "__main__":

  parser = argparse.ArgumentParser(prog='get_mask.py',
    description='Get a mask file in .tif format from the mask heap',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('inFile', help='input AOI shapefile')
  parser.add_argument('-maskType', help='mask to be used (default: visnav)',
    default='visnav')
  parser.add_argument('-maskClass', help='class to be extracted from class ' \
    '(default: water)', default='water')
  parser.add_argument('-maskThreshold', help='minimum mask area to be kept ' \
    '(default: 5000000)', default=5000000)
  parser.add_argument('-maskBuffer', help='buffer applied to polygon ' \
    '(default: -200) [m]', default=-200)
  parser.add_argument('outBase', help='output mask basename')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  get_mask(args.inFile, args.maskType.upper(), args.maskClass.upper(),
    float(args.maskThreshold), float(args.maskBuffer), args.outBase)
