#!/usr/bin/python

import os
import sys
import csv
from datetime import datetime, timedelta
from osgeo import gdal, ogr, osr
from osgeo.gdalconst import GA_ReadOnly
from scipy import ndimage
import numpy as np
import netCDF4 as nc
from asf_geometry import *
from statsmodels.tsa.seasonal import seasonal_decompose
import statsmodels.api as sm
import pandas as pd
from scipy.interpolate import interp1d
from sklearn.metrics import mean_squared_error

tolerance = 0.00005


def initializeNetcdf(ncFile, meta):

  dataset = nc.Dataset(ncFile, 'w', format='NETCDF4')

  ### Define global attributes
  dataset.Conventions = ('CF-1.7')
  dataset.institution = meta['institution']
  dataset.title = meta['title']
  dataset.source = meta['source']
  dataset.comment = meta['comment']
  dataset.reference = meta['reference']
  timestamp = datetime.utcnow().isoformat() + 'Z'
  dataset.history = ('{0}: netCDF file created'.format(timestamp))
  dataset.featureType = ('timeSeries')

  ### Create dimensions
  dataset.createDimension('xgrid', meta['cols'])
  dataset.createDimension('ygrid', meta['rows'])
  dataset.createDimension('time', None)
  dataset.createDimension('nchar', 100)

  ### Create variables - time, coordinates, values
  ## time
  time = dataset.createVariable('time', np.float32, ('time',))
  time.axis = ('T')
  time.long_name = ('serial date')
  time.standard_name = ('time')
  time.units = ('seconds since {0}'.format(meta['refTime']))
  time.calendar = 'gregorian'
  time.fill_value = 0
  time.reference = ('center time of image')

  ## map projection
  projSpatialRef = osr.SpatialReference()
  projSpatialRef.ImportFromEPSG(int(meta['epsg']))
  wkt = projSpatialRef.ExportToWkt()
  projection = dataset.createVariable('Transverse_Mercator', 'S1')
  projection.grid_mapping_name = ('transverse_mercator')
  projection.crs_wkt = wkt
  projection.scale_factor_at_centeral_meridian = \
    projSpatialRef.GetProjParm(osr.SRS_PP_SCALE_FACTOR)
  projection.longitude_of_central_meridian = \
    projSpatialRef.GetProjParm(osr.SRS_PP_CENTRAL_MERIDIAN)
  projection.latitude_of_projection_origin = \
    projSpatialRef.GetProjParm(osr.SRS_PP_LATITUDE_OF_ORIGIN)
  projection.false_easting = \
    projSpatialRef.GetProjParm(osr.SRS_PP_FALSE_EASTING)
  projection.false_northing = \
    projSpatialRef.GetProjParm(osr.SRS_PP_FALSE_NORTHING)
  projection.projection_x_coordinate = ('xgrid')
  projection.projection_y_coordinate = ('ygrid')
  projection.units = ('meters')

  ## coordinate: x grid
  xgrid = dataset.createVariable('xgrid', np.float32, ('xgrid'))
  xgrid.axis = ('X')
  xgrid.long_name = ('projection_grid_y_center')
  xgrid.standard_name = ('projection_y_coordinate')
  xgrid.units = ('meters')
  xgrid.fill_value = np.nan

  ## coordinate: y grid
  ygrid = dataset.createVariable('ygrid', np.float32, ('ygrid'))
  ygrid.axis = ('Y')
  ygrid.long_name = ('projection_grid_x_center')
  ygrid.standard_name = ('projection_x_coordinate')
  ygrid.units = ('meters')
  ygrid.fill_value = np.nan

  ## image
  image = dataset.createVariable('image', np.float32, \
    ('time', 'ygrid', 'xgrid'), zlib=True)
  image.long_name = meta['imgLongName']
  image.units = meta['imgUnits']
  image.fill_value = meta['imgNoData']

  ## name
  name = dataset.createVariable('granule', 'S1', ('time', 'nchar'))
  name.long_name = 'name of the granule'

  ### Fill in coordinates
  xCoordinate = np.arange(meta['minX'], meta['maxX'], meta['pixelSize'])
  xgrid[:] = xCoordinate
  yCoordinate = np.arange(meta['maxY'], meta['minY'], -meta['pixelSize'])
  ygrid[:] = yCoordinate

  dataset.close()


def nc2meta(ncFile):

  dataset = nc.Dataset(ncFile, 'r')

  meta = {}

  ### Global attributes
  meta['conventions'] = dataset.Conventions
  meta['institution'] = dataset.institution
  meta['title'] = dataset.title
  meta['source'] = dataset.source
  meta['comment'] = dataset.comment
  meta['reference'] = dataset.reference

  ### Coordinates
  xGrid = dataset.variables['xgrid']
  (meta['cols'],) = xGrid.shape
  meta['pixelSize'] = xGrid[1] - xGrid[0]
  meta['minX'] = np.min(xGrid)
  meta['maxX'] = np.max(xGrid) + meta['pixelSize']
  yGrid = dataset.variables['ygrid']
  (meta['rows'],) = yGrid.shape
  meta['minY'] = np.min(yGrid) - meta['pixelSize']
  meta['maxY'] = np.max(yGrid)

  ### Time reference
  time = dataset.variables['time']
  (meta['timeCount'],) = time.shape
  meta['refTime'] = time.units[14:]

  ### Map projection: EPSG
  proj = dataset.variables['Transverse_Mercator']
  projSpatialRef = osr.SpatialReference()
  projSpatialRef.ImportFromWkt(proj.crs_wkt)
  meta['epsg'] = int(projSpatialRef.GetAttrValue('AUTHORITY', 1))

  ### Image metadata
  image = dataset.variables['image']
  meta['imgLongName'] = image.long_name
  meta['imgUnits'] = image.units
  meta['imgNoData'] = image.fill_value

  dataset.close()

  return meta


def addImage2netcdf(image, ncFile, granule, imgTime):

  dataset = nc.Dataset(ncFile, 'a')

  ### Updating time
  time = dataset.variables['time']
  name = dataset.variables['granule']
  data = dataset.variables['image']
  numGranules = time.shape[0]
  time[numGranules] = nc.date2num(imgTime, units=time.units,
    calendar=time.calendar)
  name[numGranules] = nc.stringtochar(np.array(granule, 'S100'))
  data[numGranules,:,:] = image

  dataset.close()


def reproject2grid(inRaster, tsEPSG):

  # Read basic metadata
  cols = inRaster.RasterXSize
  rows = inRaster.RasterYSize
  geoTrans = inRaster.GetGeoTransform()
  proj = osr.SpatialReference()
  proj.ImportFromEPSG(tsEPSG)

  # Define warping options
  rasterFormat = 'VRT'
  xRes = geoTrans[1]
  yRes = xRes
  resampleAlg = gdal.GRA_Bilinear
  options = ['COMPRESS=DEFLATE']

  outRaster = gdal.Warp('', inRaster, format=rasterFormat, dstSRS=proj,
    targetAlignedPixels=True, xRes=xRes, yRes=yRes, resampleAlg=resampleAlg,
    options=options)
  inRaster = None

  return outRaster


def apply_mask(data, dataGeoTrans, mask, maskGeoTrans):

  (dataRows, dataCols) = data.shape
  dataOriginX = dataGeoTrans[0]
  dataOriginY = dataGeoTrans[3]
  dataPixelSize = dataGeoTrans[1]
  (maskRows, maskCols) = mask.shape
  maskOriginX = maskGeoTrans[0]
  maskOriginY = maskGeoTrans[3]
  maskPixelSize = maskGeoTrans[1]
  offsetX = int(np.rint((maskOriginX - dataOriginX)/maskPixelSize))
  offsetY = int(np.rint((dataOriginY - maskOriginY)/maskPixelSize))
  data = data[offsetY:maskRows+offsetY,offsetX:maskCols+offsetX]
  mask[mask==0] = np.nan
  data *= mask

  return data


def filter_change(image, kernelSize, iterations):

  (cols, rows) = image.shape
  positiveChange = np.zeros((rows,cols), dtype=np.uint8)
  negativeChange = np.zeros((rows,cols), dtype=np.uint8)
  noChange = np.zeros((rows,cols), dtype=np.uint8)
  for ii in range(int(cols)):
    for kk in range(int(rows)):
      if image[ii,kk] == 1:
        negativeChange[ii,kk] = 1
      elif image[ii,kk] == 2:
        noChange = 1
      elif image[ii,kk] == 3:
        positiveChange[ii,kk] = 1
  image = None
  positiveChange = ndimage.binary_opening(positiveChange,
    iterations=iterations, structure=np.ones(kernelSize)).astype(np.uint8)
  negativeChange = ndimage.binary_opening(negativeChange,
    iterations=iterations, structure=np.ones(kernelSize)).astype(np.uint8)
  change = np.full((rows,cols), 2, dtype=np.uint8)
  for ii in range(int(cols)):
    for kk in range(int(rows)):
      if negativeChange[ii,kk] == 1:
        change[ii,kk] = 1
      elif positiveChange[ii,kk] == 1:
        change[ii,kk] = 3
  change *= noChange

  return change


def geotiff2data(inGeotiff):

  inRaster = gdal.Open(inGeotiff)
  proj = osr.SpatialReference()
  proj.ImportFromWkt(inRaster.GetProjectionRef())
  if proj.GetAttrValue('AUTHORITY', 0) == 'EPSG':
    epsg = int(proj.GetAttrValue('AUTHORITY', 1))
  geoTrans = inRaster.GetGeoTransform()
  inBand = inRaster.GetRasterBand(1)
  noData = inBand.GetNoDataValue()
  data = inBand.ReadAsArray()
  if data.dtype == np.uint8:
    dtype = 'BYTE'
  elif data.dtype == np.float32:
    dtype = 'FLOAT'

  return (data, geoTrans, proj, epsg, dtype, noData)


def data2geotiff(data, geoTrans, proj, dtype, noData, outFile):

  (rows, cols) = data.shape
  gdalDriver = gdal.GetDriverByName('GTiff')
  if dtype == 'BYTE':
    outRaster = gdalDriver.Create(outFile, cols, rows, 1, gdal.GDT_Byte,
      ['COMPRESS=DEFLATE'])
  elif dtype == 'FLOAT':
    outRaster = gdalDriver.Create(outFile, cols, rows, 1, gdal.GDT_Float32,
      ['COMPRESS=DEFLATE'])
  outRaster.SetGeoTransform(geoTrans)
  outRaster.SetProjection(proj.ExportToWkt())
  outBand = outRaster.GetRasterBand(1)
  outBand.SetNoDataValue(noData)
  outBand.WriteArray(data)
  outRaster = None


def raster_meta(rasterFile):

  raster = gdal.Open(rasterFile)
  spatialRef = osr.SpatialReference()
  spatialRef.ImportFromWkt(raster.GetProjectionRef())
  gt = raster.GetGeoTransform()
  shape = [ raster.RasterYSize, raster.RasterXSize ]
  pixel = raster.GetMetadataItem('AREA_OR_POINT')
  raster = None

  return (spatialRef, gt, shape, pixel)


def vector_meta(vectorFile):

  vector = ogr.Open(vectorFile)
  layer = vector.GetLayer()
  layerDefinition = layer.GetLayerDefn()
  fieldCount = layerDefinition.GetFieldCount()
  fields = []
  field = {}
  for ii in range(fieldCount):
    field['name'] = layerDefinition.GetFieldDefn(ii).GetName()
    fieldType = layerDefinition.GetFieldDefn(ii).GetType()
    field['type'] = layerDefinition.GetFieldDefn(ii).GetFieldTypeName(fieldType)
    field['width'] = layerDefinition.GetFieldDefn(ii).GetWidth()
    field['precision'] = layerDefinition.GetFieldDefn(ii).GetPrecision()
    fields.append(field)
  proj = layer.GetSpatialRef()
  extent = layer.GetExtent()
  features = []
  featureCount = layer.GetFeatureCount()
  for feature in layer:
    geometry = feature.GetGeometryRef()
    features.append(geometry.GetGeometryName())

  return (fields, proj, extent, features)


def raster_metadata(input):

  # Set up shapefile attributes
  fields = []
  field = {}
  values = []
  field['name'] = 'granule'
  field['type'] = ogr.OFTString
  field['width'] = 254
  fields.append(field)
  field = {}
  field['name'] = 'epsg'
  field['type'] = ogr.OFTInteger
  fields.append(field)
  field = {}
  field['name'] = 'originX'
  field['type'] = ogr.OFTReal
  fields.append(field)
  field = {}
  field['name'] = 'originY'
  field['type'] = ogr.OFTReal
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
  field['name'] = 'pixel'
  field['type'] = ogr.OFTString
  field['width'] = 8
  fields.append(field)

  # Extract other raster image metadata
  (outSpatialRef, outGt, outShape, outPixel) = raster_meta(input)
  if outSpatialRef.GetAttrValue('AUTHORITY', 0) == 'EPSG':
    epsg = int(outSpatialRef.GetAttrValue('AUTHORITY', 1))

  # Add granule name and geometry
  base = os.path.basename(input)
  granule = os.path.splitext(base)[0]
  value = {}
  value['granule'] = granule
  value['epsg'] = epsg
  value['originX'] = outGt[0]
  value['originY'] = outGt[3]
  value['pixSize'] = outGt[1]
  value['cols'] = outShape[1]
  value['rows'] = outShape[0]
  value['pixel'] = outPixel
  values.append(value)

  return (fields, values, outSpatialRef)


def time_series_slice(ncFile, x, y, typeXY):

  timeSeries = nc.Dataset(ncFile, 'r')

  ### Extract information for variables: image, time, granule
  timeRef = timeSeries.variables['time'].getncattr('units')[14:]
  timeRef = datetime.strptime(timeRef, '%Y-%m-%d %H:%M:%S')
  time = timeSeries.variables['time'][:].tolist()
  timestamp = []
  for t in time:
    timestamp.append(timeRef + timedelta(seconds=t))
  xGrid = timeSeries.variables['xgrid'][:]
  yGrid = timeSeries.variables['ygrid'][:]
  granules = timeSeries.variables['granule']
  granule = nc.chartostring(granules[:])
  data = timeSeries.variables['image']
  numGranules = len(time)

  ### Define geo transformation and map proejction
  originX = xGrid[0]
  originY = yGrid[0]
  pixelSize = xGrid[1] - xGrid[0]
  gt = (originX, pixelSize, 0, originY, 0, -pixelSize)
  var = timeSeries.variables.keys()
  if 'Transverse_Mercator' in var:
    wkt = timeSeries.variables['Transverse_Mercator'].getncattr('crs_wkt')
  else:
    print('Could not find map projection information!')
    sys.exit(1)

  ### Work out line/sample from various input types
  if typeXY == 'pixel':
    sample = x
    line = y
  elif typeXY == 'latlon':
    inProj = osr.SpatialReference()
    inProj.ImportFromEPSG(4326)
    outProj = osr.SpatialReference()
    outProj.ImportFromWkt(wkt)
    transform = osr.CoordinateTransformation(inProj, outProj)
    coord = ogr.Geometry(ogr.wkbPoint)
    coord.AddPoint(x,y)
    coord.Transform(transform)
    coordX = np.rint(coord.GetX()/pixelSize)*pixelSize
    coordY = np.rint(coord.GetY()/pixelSize)*pixelSize
    sample = xGrid.tolist().index(coordX)
    line = yGrid.tolist().index(coordY)
  elif typeXY == 'mapXY':
    sample = xGrid.tolist().index(x)
    line = yGrid.tolist().index(y)
  value = data[:,sample,line]

  ### Work on time series
  ## Fill in gaps by interpolation
  startDate = timestamp[0].date()
  stopDate = timestamp[len(timestamp)-1].date()
  refDates = np.arange(startDate, stopDate + timedelta(days=12), 12).tolist()
  datestamp = []
  for t in time:
    datestamp.append((timeRef + timedelta(seconds=t)).date())
  missingDates = list(set(refDates) - set(datestamp))
  f = interp1d(time, value)
  missingTime = []
  for missingDate in missingDates:
    missingTime.append((missingDate - timeRef.date()).total_seconds())
  missingValues = f(missingTime)
  allValues = []
  refType = []
  for ii in range(len(refDates)):
    if refDates[ii] in missingDates:
      index = missingDates.index(refDates[ii])
      allValues.append(missingValues[index])
      refType.append('interpolated')
    else:
      index = datestamp.index(refDates[ii])
      allValues.append(value[index])
      refType.append('acquired')
  allValues = np.asarray(allValues)

  ## Smoothing the time line with localized regression (LOESS)
  lowess = sm.nonparametric.lowess
  smooth = lowess(allValues, np.arange(len(allValues)), frac=0.08, it=0)[:,1]

  sd = seasonal_decompose(x=smooth, model='additive', freq=4)

  return (granule, refDates, refType, smooth, sd)
