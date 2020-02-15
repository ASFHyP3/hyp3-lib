#!/usr/bin/python3

import os
import sys
from datetime import datetime, timedelta
from osgeo import gdal, ogr, osr
from scipy import ndimage
import numpy as np
import netCDF4 as nc
from statsmodels.tsa.seasonal import seasonal_decompose
import statsmodels.api as sm
from scipy.interpolate import interp1d
from asf_geometry import geometry_proj2geo, raster_meta

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

# Lets other tools use this without reading from directory:
def getNetcdfTime(ncFile):
  timeSeries = nc.Dataset(ncFile, 'r')
  timeRef = ncFile.variables['time'][:].getncattr('units')[14:]
  timeRef = datetime.strptime(timeRef, '%Y-%m-%d %H:%M:%S')
  time = ncFile.variables['time'][:].tolist()
  timestamps = []
  for t in time:
    timestamp = timeRef + timedelta(seconds=t)
    timestamps.append(timestamp.isoformat())
  return timestamps

def extractNetcdfTime(ncFilePath, csvFile):
  outF = open(csvFile, 'w')
  ncFile = nc.Dataset(ncFilePath, 'r')

  timestamps = getNetcdfTime(ncFile)
  for t in timestamps:
    outF.write('%s\n' % t)
  outF.close()
  ncFile.close()

def getNetcdfGranule(ncFile):
  granules = ncFile.variables['granule']
  granules = nc.chartostring(granules[:])
  return list(granules)

def extractNetcdfGranule(ncFilePath, csvFile):
  outF = open(csvFile, 'w')
  ncFile = nc.Dataset(ncFilePath, 'r')

  granules = getNetcdfGranule(ncFile)
  for g in granules:
    outF.write('%s\n' % g)
  outF.close()
  ncFile.close()


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
  meta['history'] = dataset.history

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


def vector_meta(vectorFile):

  vector = ogr.Open(vectorFile)
  layer = vector.GetLayer()
  layerDefinition = layer.GetLayerDefn()
  fieldCount = layerDefinition.GetFieldCount()
  fields = []
  for ii in range(fieldCount):
    field = {}
    field['name'] = layerDefinition.GetFieldDefn(ii).GetName()
    field['type'] = layerDefinition.GetFieldDefn(ii).GetType()
    field['width'] = layerDefinition.GetFieldDefn(ii).GetWidth()
    field['precision'] = layerDefinition.GetFieldDefn(ii).GetPrecision()
    fields.append(field)
  proj = layer.GetSpatialRef()
  extent = layer.GetExtent()
  features = []
  featureCount = layer.GetFeatureCount()
  for kk in range(featureCount):
    value = {}
    feature = layer.GetFeature(kk)
    for ii in range(fieldCount):
      if fields[ii]['type'] == ogr.OFTInteger:
        value[fields[ii]['name']] = int(feature.GetField(ii))
      elif fields[ii]['type'] == ogr.OFTReal:
        value[fields[ii]['name']] = float(feature.GetField(ii))
      else:
        value[fields[ii]['name']] = feature.GetField(ii)
    value['geometry'] = feature.GetGeometryRef().ExportToWkt()
    features.append(value)

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


def netcdf2boundary_mask(ncFile, geographic):

  ### Extract metadata
  meta = nc2meta(ncFile)
  cols = meta['cols']
  rows = meta['rows']
  ntimes = meta['timeCount']
  proj = osr.SpatialReference()
  proj.ImportFromEPSG(meta['epsg'])
  geoTrans = \
    (meta['minX'], meta['pixelSize'], 0, meta['maxY'], 0, -meta['pixelSize'])

  ### Reading time series
  dataset = nc.Dataset(ncFile, 'r')
  image = dataset.variables['image'][:]
  dataset.close()

  ### Save in memory
  data = image[0,:,:]/image[0,:,:]
  image = None
  gdalDriver = gdal.GetDriverByName('Mem')
  outRaster = gdalDriver.Create('out', rows, cols, 1, gdal.GDT_Byte)
  outRaster.SetGeoTransform(geoTrans)
  outRaster.SetProjection(proj.ExportToWkt())
  outBand = outRaster.GetRasterBand(1)
  outBand.WriteArray(data)
  inBand = None
  inRaster = None
  data = None

  ### Polygonize the raster image
  inBand = outRaster.GetRasterBand(1)
  ogrDriver = ogr.GetDriverByName('Memory')
  outVector = ogrDriver.CreateDataSource('out')
  outLayer = outVector.CreateLayer('boundary', srs=proj)
  fieldDefinition = ogr.FieldDefn('ID', ogr.OFTInteger)
  outLayer.CreateField(fieldDefinition)
  gdal.Polygonize(inBand, inBand, outLayer, 0, [], None)
  outRaster = None

  ### Extract geometry from layer
  inSpatialRef = outLayer.GetSpatialRef()
  multipolygon = ogr.Geometry(ogr.wkbMultiPolygon)
  for outFeature in outLayer:
    geometry = outFeature.GetGeometryRef()
    multipolygon.AddGeometry(geometry)
    outFeature = None
  outLayer = None

  ### Convert geometry from projected to geographic coordinates (if requested)
  if geographic == True:
    (multipolygon, outSpatialRef) = \
      geometry_proj2geo(multipolygon, inSpatialRef)
    return (multipolygon, outSpatialRef)
  else:
    return (multipolygon, inSpatialRef)


def time_series_slice(ncFile, sample, line):

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
  value = data[:,sample,line]

  return (granule, timestamp, value)
