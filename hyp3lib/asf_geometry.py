import csv
import os

import numpy as np
from osgeo import gdal, ogr, osr
from osgeo.gdalconst import GA_ReadOnly
from scipy import ndimage

from hyp3lib import GeometryError
from hyp3lib.saa_func_lib import get_zone


# Determine the boundary polygon of a GeoTIFF file
def geotiff2polygon_ext(geotiff):

  raster = gdal.Open(geotiff)
  proj = osr.SpatialReference()
  proj.ImportFromWkt(raster.GetProjectionRef())
  gt = raster.GetGeoTransform()
  originX = gt[0]
  originY = gt[3]
  pixelWidth = gt[1]
  pixelHeight = gt[5]
  cols = raster.RasterXSize
  rows = raster.RasterYSize
  polygon = ogr.Geometry(ogr.wkbPolygon)
  ring = ogr.Geometry(ogr.wkbLinearRing)
  ring.AddPoint_2D(originX, originY)
  ring.AddPoint_2D(originX + cols*pixelWidth, originY)
  ring.AddPoint_2D(originX + cols*pixelWidth, originY + rows*pixelHeight)
  ring.AddPoint_2D(originX, originY + rows*pixelHeight)
  ring.AddPoint_2D(originX, originY)
  polygon.AddGeometry(ring)
  ring = None
  raster = None

  return (polygon, proj)


def geotiff2polygon(geotiff):

  (polygon, proj) = geotiff2polygon_ext(geotiff)
  return polygon


def geotiff2boundary_mask(inGeotiff, tsEPSG, threshold, use_closing=True):

  inRaster = gdal.Open(inGeotiff)
  proj = osr.SpatialReference()
  proj.ImportFromWkt(inRaster.GetProjectionRef())
  if proj.GetAttrValue('AUTHORITY', 0) == 'EPSG':
    epsg = int(proj.GetAttrValue('AUTHORITY', 1))

  if tsEPSG != 0 and epsg != tsEPSG:
    print('Reprojecting ...')
    inRaster = reproject2grid(inRaster, tsEPSG)
    proj.ImportFromWkt(inRaster.GetProjectionRef())
    if proj.GetAttrValue('AUTHORITY', 0) == 'EPSG':
      epsg = int(proj.GetAttrValue('AUTHORITY', 1))

  geoTrans = inRaster.GetGeoTransform()
  inBand = inRaster.GetRasterBand(1)
  noDataValue = inBand.GetNoDataValue()
  data = inBand.ReadAsArray()
  minValue = np.min(data)

  ### Check for black fill
  if minValue > 0:
    data /= data
    colFirst = 0
    rowFirst = 0
  else:
    data[np.isnan(data)==True] = noDataValue
    if threshold is not None:
      print('Applying threshold ({0}) ...'.format(threshold))
      data[data<np.float(threshold)] = noDataValue
    if noDataValue == np.nan or noDataValue == -np.nan:
      data[np.isnan(data)==False] = 1
    else:
      data[data>noDataValue] = 1
    if use_closing:
      data = ndimage.binary_closing(data, iterations=10,
        structure=np.ones((3,3))).astype(data.dtype)
    inRaster = None

    (data, colFirst, rowFirst, geoTrans) = cut_blackfill(data, geoTrans)

  return (data, colFirst, rowFirst, geoTrans, proj)


def reproject2grid(inRaster, tsEPSG, xRes = None ):

  # Read basic metadata
  geoTrans = inRaster.GetGeoTransform()
  proj = osr.SpatialReference()
  proj.ImportFromEPSG(tsEPSG)

  # Define warping options
  rasterFormat = 'VRT'
  if xRes is None:
      xRes = geoTrans[1]
  yRes = xRes
  resampleAlg = gdal.GRA_Bilinear
  options = ['COMPRESS=DEFLATE']

  outRaster = gdal.Warp('', inRaster, format=rasterFormat, dstSRS=proj,
    targetAlignedPixels=True, xRes=xRes, yRes=yRes, resampleAlg=resampleAlg,
    options=options)
  inRaster = None

  return outRaster


def cut_blackfill(data, geoTrans):

  originX = geoTrans[0]
  originY = geoTrans[3]
  pixelSize = geoTrans[1]
  colProfile = list(data.max(axis=1))
  rows = colProfile.count(1)
  rowFirst = colProfile.index(1)
  rowProfile = list(data.max(axis=0))
  cols = rowProfile.count(1)
  colFirst = rowProfile.index(1)
  originX += colFirst*pixelSize
  originY -= rowFirst*pixelSize
  data = data[rowFirst:rows+rowFirst,colFirst:cols+colFirst]
  geoTrans = (originX, pixelSize, 0, originY, 0, -pixelSize)

  return (data, colFirst, rowFirst, geoTrans)


def geotiff_overlap(firstFile, secondFile, method):

  # Check map projections
  raster = gdal.Open(firstFile)
  proj = raster.GetProjection()
  gt = raster.GetGeoTransform()
  pixelSize = gt[1]
  raster = None

  # Extract boundary polygons
  firstPolygon = geotiff2polygon(firstFile)
  secondPolygon = geotiff2polygon(secondFile)

  if method == 'intersection':
    overlap = firstPolygon.Intersection(secondPolygon)
  elif method == 'union':
    overlap = firstPolygon.Union(secondPolygon)

  return (firstPolygon, secondPolygon, overlap, proj, pixelSize)


def overlap_indices(polygon, boundary, pixelSize):

  polyEnv = polygon.GetEnvelope()
  boundEnv = boundary.GetEnvelope()
  xOff = int((boundEnv[0] - polyEnv[0]) / pixelSize)
  yOff = int((polyEnv[3] - boundEnv[3]) / pixelSize)
  xCount = int((boundEnv[1] - boundEnv[0]) / pixelSize)
  yCount = int((boundEnv[3] - boundEnv[2]) / pixelSize)

  return (xOff, yOff, xCount, yCount)


# Extract geometry from shapefile
def shape2geometry(shapeFile, field):

  name = []
  fields = []
  driver = ogr.GetDriverByName('ESRI Shapefile')
  shape = driver.Open(shapeFile, 0)
  multipolygon = ogr.Geometry(ogr.wkbMultiPolygon)
  layer = shape.GetLayer()
  spatialRef = layer.GetSpatialRef()
  layerDef = layer.GetLayerDefn()
  for i in range(layerDef.GetFieldCount()):
    fields.append(layerDef.GetFieldDefn(i).GetName())
  if field not in fields:
    return (None, None, None)
  for feature in layer:
    geometry = feature.GetGeometryRef()
    count = geometry.GetGeometryCount()
    if geometry.GetGeometryName() == 'MULTIPOLYGON':
      for i in range(0, count):
        polygon = geometry.GetGeometryRef(i)
        multipolygon.AddGeometry(polygon)
        name.append(feature.GetField(field))
    else:
      multipolygon.AddGeometry(geometry)
      name.append(feature.GetField(field))
  shape.Destroy()

  return (multipolygon, spatialRef, name)


def shape2geometry_ext(shapeFile):

  values = []
  fields = []
  driver = ogr.GetDriverByName('ESRI Shapefile')
  shape = driver.Open(shapeFile, 0)
  layer = shape.GetLayer()
  spatialRef = layer.GetSpatialRef()
  layerDef = layer.GetLayerDefn()
  featureCount = layerDef.GetFieldCount()
  for ii in range(featureCount):
    field = {}
    field['name'] = layerDef.GetFieldDefn(ii).GetName()
    field['type'] = layerDef.GetFieldDefn(ii).GetType()
    if field['type'] == ogr.OFTString:
      field['width'] = layerDef.GetFieldDefn(ii).GetWidth()
    fields.append(field)
  for feature in layer:
    multipolygon = ogr.Geometry(ogr.wkbMultiPolygon)
    geometry = feature.GetGeometryRef()
    count = geometry.GetGeometryCount()
    if geometry.GetGeometryName() == 'MULTIPOLYGON':
      for i in range(0, count):
        polygon = geometry.GetGeometryRef(i)
        multipolygon.AddGeometry(polygon)
    else:
      multipolygon.AddGeometry(geometry)
    value = {}
    for field in fields:
      value[field['name']] = feature.GetField(field['name'])
    value['geometry'] = multipolygon
    values.append(value)
  shape.Destroy()

  return (fields, values, spatialRef)


# Save geometry with fields to shapefile
def geometry2shape(fields, values, spatialRef, merge, shapeFile):

  driver = ogr.GetDriverByName('ESRI Shapefile')
  if os.path.exists(shapeFile):
    driver.DeleteDataSource(shapeFile)
  outShape = driver.CreateDataSource(shapeFile)
  outLayer = outShape.CreateLayer('layer', srs=spatialRef)
  for field in fields:
    fieldDefinition = ogr.FieldDefn(field['name'], field['type'])
    if field['type'] == ogr.OFTString:
      fieldDefinition.SetWidth(field['width'])
    elif field['type'] == ogr.OFTReal:
      fieldDefinition.SetWidth(24)
      fieldDefinition.SetPrecision(8)
    outLayer.CreateField(fieldDefinition)
  featureDefinition = outLayer.GetLayerDefn()
  if merge == True:
    combine = ogr.Geometry(ogr.wkbMultiPolygon)
    for value in values:
      combine = combine.Union(value['geometry'])
    outFeature = ogr.Feature(featureDefinition)
    for field in fields:
      name = field['name']
      outFeature.SetField(name, 'multipolygon')
    outFeature.SetGeometry(combine)
    outLayer.CreateFeature(outFeature)
    outFeature.Destroy()
  else:
    for value in values:
      outFeature = ogr.Feature(featureDefinition)
      for field in fields:
        name = field['name']
        outFeature.SetField(name, value[name])
      outFeature.SetGeometry(value['geometry'])
      outLayer.CreateFeature(outFeature)
      outFeature.Destroy()
  outShape.Destroy()


# Save data with fields to shapefile
def data_geometry2shape_ext(data, fields, values, spatialRef, geoTrans,
  classes, threshold, background, shapeFile):

  # Check input
  if threshold is not None:
    threshold = float(threshold)
  if background is not None:
    background = int(background)

  # Buffer data
  (rows, cols) = data.shape
  pixelSize = geoTrans[1]
  originX = geoTrans[0] - 10*pixelSize
  originY = geoTrans[3] + 10*pixelSize
  geoTrans = (originX, pixelSize, 0, originY, 0, -pixelSize)
  mask = np.zeros((rows+20, cols+20), dtype=np.float32)
  mask[10:rows+10,10:cols+10] = data
  data = mask

  # Save in memory
  (rows, cols) = data.shape
  data = data.astype(np.byte)
  gdalDriver = gdal.GetDriverByName('Mem')
  outRaster = gdalDriver.Create('value', cols, rows, 1, gdal.GDT_Byte)
  outRaster.SetGeoTransform(geoTrans)
  outRaster.SetProjection(spatialRef.ExportToWkt())
  outBand = outRaster.GetRasterBand(1)
  outBand.WriteArray(data)

  # Write data to shapefile
  driver = ogr.GetDriverByName('ESRI Shapefile')
  if os.path.exists(shapeFile):
    driver.DeleteDataSource(shapeFile)
  outShape = driver.CreateDataSource(shapeFile)
  outLayer = outShape.CreateLayer('polygon', srs=spatialRef)
  outField = ogr.FieldDefn('value', ogr.OFTInteger)
  outLayer.CreateField(outField)
  gdal.Polygonize(outBand, None, outLayer, 0, [], callback=None)
  for field in fields:
    fieldDefinition = ogr.FieldDefn(field['name'], field['type'])
    if field['type'] == ogr.OFTString:
      fieldDefinition.SetWidth(field['width'])
    outLayer.CreateField(fieldDefinition)
  fieldDefinition = ogr.FieldDefn('area', ogr.OFTReal)
  fieldDefinition.SetWidth(16)
  fieldDefinition.SetPrecision(3)
  outLayer.CreateField(fieldDefinition)
  fieldDefinition = ogr.FieldDefn('centroid', ogr.OFTString)
  fieldDefinition.SetWidth(50)
  outLayer.CreateField(fieldDefinition)
  if classes:
    fieldDefinition = ogr.FieldDefn('size', ogr.OFTString)
    fieldDefinition.SetWidth(25)
    outLayer.CreateField(fieldDefinition)
  _ = outLayer.GetLayerDefn()
  for outFeature in outLayer:
    for value in values:
      for field in fields:
        name = field['name']
        outFeature.SetField(name, value[name])
    cValue = outFeature.GetField('value')
    fill = False
    if cValue == 0:
      fill = True
    if background is not None and cValue == background:
      fill = True
    geometry = outFeature.GetGeometryRef()
    area = float(geometry.GetArea())
    outFeature.SetField('area', area)
    if classes:
      for ii in range(len(classes)):
        if area > classes[ii]['minimum'] and area < classes[ii]['maximum']:
          outFeature.SetField('size',classes[ii]['class'])
    centroid = geometry.Centroid().ExportToWkt()
    outFeature.SetField('centroid', centroid)
    if fill == False and area > threshold:
      outLayer.SetFeature(outFeature)
    else:
      outLayer.DeleteFeature(outFeature.GetFID())
  outShape.Destroy()


def data_geometry2shape(data, fields, values, spatialRef, geoTrans, shapeFile):

  return data_geometry2shape_ext(data, fields, values, spatialRef, geoTrans,
    None, 0, None, shapeFile)


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
  elif data.dtype == np.float64:
    dtype = 'DOUBLE'

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


# Save raster information (fields, values) to CSV file
def raster2csv(fields, values, csvFile):

  header = []
  for field in fields:
    header.append(field['name'])
  line = []
  for value in values:
    for field in fields:
      name = field['name']
      line.append(value[name])

  with open(csvFile, 'wb') as outF:
    writer = csv.writer(outF, delimiter=';')
    writer.writerow(header)
    writer.writerow(line)


# Combine all geometries in a list
def union_geometries(geometries):

  combine = ogr.Geometry(ogr.wkbMultiPolygon)
  for geometry in geometries:
    combine = combine.Union(geometry)

  return combine


def spatial_query(source, reference, function):

  # Extract information from tiles and boundary shapefiles
  (geoTile, spatialRef, nameTile) = shape2geometry(reference, 'tile')
  if geoTile is None:
    raise GeometryError(f'Could not extract information (tile) out of shapefile {reference}')
  (boundary, spatialRef, granule) = shape2geometry(source, 'granule')
  if boundary is None:
    raise GeometryError(f'Could not extract information (granule) out of shapefile {source}')

  # Perform the spatial analysis
  i = 0
  tile = []
  multipolygon = ogr.Geometry(ogr.wkbMultiPolygon)
  for geo in geoTile:
    for bound in boundary:
      if function == 'intersects':
        intersection = bound.Intersection(geo)
        if intersection.GetGeometryName() == 'POLYGON':
          if nameTile[i] not in tile:
            tile.append(nameTile[i])
            multipolygon.AddGeometry(geo)
    i = i + 1

  return (multipolygon, tile)


# Converted geometry from projected to geographic
def geometry_proj2geo(inMultipolygon, inSpatialRef):

  outSpatialRef = osr.SpatialReference()
  outSpatialRef.ImportFromEPSG(4326)
  coordTrans = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)
  outMultipolygon = ogr.Geometry(ogr.wkbMultiPolygon)
  for polygon in inMultipolygon:
    if inSpatialRef != outSpatialRef:
      polygon.Transform(coordTrans)
    outMultipolygon.AddGeometry(polygon)

  return (outMultipolygon, outSpatialRef)

# Convert corner points from geographic to UTM projection
def geometry_geo2proj(lat_max,lat_min,lon_max,lon_min):

    zone = get_zone(lon_min,lon_max)
    if (lat_min+lat_max)/2 > 0:
        proj = ('326%02d' % int(zone))
    else:
        proj = ('327%02d' % int(zone))

    inSpatialRef = osr.SpatialReference()
    inSpatialRef.ImportFromEPSG(4326)
    outSpatialRef = osr.SpatialReference()
    outSpatialRef.ImportFromEPSG(int(proj))
    coordTrans = osr.CoordinateTransformation(inSpatialRef,outSpatialRef)

    x1, y1, h = coordTrans.TransformPoint(lon_max, lat_min)
    x2, y2, h = coordTrans.TransformPoint(lon_min, lat_min)
    x3, y3, h = coordTrans.TransformPoint(lon_max, lat_max)
    x4, y4, h = coordTrans.TransformPoint(lon_min, lat_max)

    y_min = min(y1,y2,y3,y4)
    y_max = max(y1,y2,y3,y4)
    x_min = min(x1,x2,x3,x4)
    x_max = max(x1,x2,x3,x4)

    # false_easting = outSpatialRef.GetProjParm(osr.SRS_PP_FALSE_EASTING)
    false_northing = outSpatialRef.GetProjParm(osr.SRS_PP_FALSE_NORTHING)

    return zone, false_northing, y_min, y_max, x_min, x_max


def reproject_corners(corners, posting, inEPSG, outEPSG):

  # Reproject coordinates
  inProj = osr.SpatialReference()
  inProj.ImportFromEPSG(inEPSG)
  outProj = osr.SpatialReference()
  outProj.ImportFromEPSG(outEPSG)
  transform = osr.CoordinateTransformation(inProj, outProj)
  corners.Transform(transform)

  # Get extent and round to even coordinates
  (minX, maxX, minY, maxY) = corners.GetEnvelope()
  #posting = inGT[1]
  minX = np.ceil(minX/posting)*posting
  minY = np.ceil(minY/posting)*posting
  maxX = np.ceil(maxX/posting)*posting
  maxY = np.ceil(maxY/posting)*posting

  # Add points to multiPoint
  corners = ogr.Geometry(ogr.wkbMultiPoint)
  ul = ogr.Geometry(ogr.wkbPoint)
  ul.AddPoint(minX, maxY)
  corners.AddGeometry(ul)
  ll = ogr.Geometry(ogr.wkbPoint)
  ll.AddPoint(minX, minY)
  corners.AddGeometry(ll)
  ur = ogr.Geometry(ogr.wkbPoint)
  ur.AddPoint(maxX, maxY)
  corners.AddGeometry(ur)
  lr = ogr.Geometry(ogr.wkbPoint)
  lr.AddPoint(maxX, minY)
  corners.AddGeometry(lr)

  return corners


def reproject_extent(minX, maxX, minY, maxY, posting, inEPSG, outEPSG):

  # Add points to multiPoint
  corners = ogr.Geometry(ogr.wkbMultiPoint)
  ul = ogr.Geometry(ogr.wkbPoint)
  ul.AddPoint(minX, maxY)
  corners.AddGeometry(ul)
  ll = ogr.Geometry(ogr.wkbPoint)
  ll.AddPoint(minX, minY)
  corners.AddGeometry(ll)
  ur = ogr.Geometry(ogr.wkbPoint)
  ur.AddPoint(maxX, maxY)
  corners.AddGeometry(ur)
  lr = ogr.Geometry(ogr.wkbPoint)
  lr.AddPoint(maxX, minY)
  corners.AddGeometry(lr)

  # Re-project corners
  reproject_corners(corners, posting, inEPSG, outEPSG)

  # Extract min/max values
  return corners.GetEnvelope()


def raster_meta(rasterFile):

  raster = gdal.Open(rasterFile)
  spatialRef = osr.SpatialReference()
  spatialRef.ImportFromWkt(raster.GetProjectionRef())
  gt = raster.GetGeoTransform()
  shape = [ raster.RasterYSize, raster.RasterXSize ]
  pixel = raster.GetMetadataItem('AREA_OR_POINT')
  raster = None

  return (spatialRef, gt, shape, pixel)


def overlapMask(meta, maskShape, invert, outFile):

  ### Extract metadata
  posting = meta['pixelSize']
  # proj = meta['proj']
  imageEPSG = meta['epsg']
  multiBoundary = meta['boundary']
  dataRows = meta['rows']
  dataCols = meta['cols']
  geoEPSG = 4326

  ### Extract mask polygon
  ogrDriver = ogr.GetDriverByName('ESRI Shapefile')
  inShape = ogrDriver.Open(maskShape)
  outLayer = inShape.GetLayer()
  outProj = outLayer.GetSpatialRef()
  outEPSG = int(outProj.GetAttrValue('AUTHORITY', 1))
  if geoEPSG != outEPSG:
    raise GeometryError(f'Expecting mask file with EPSG code: {geoEPSG}')

  ### Define re-projection from geographic to UTM
  inProj = osr.SpatialReference()
  inProj.ImportFromEPSG(4326)
  outProj = osr.SpatialReference()
  outProj.ImportFromEPSG(imageEPSG)
  transform = osr.CoordinateTransformation(inProj, outProj)

  ### Loop through features
  for boundary in multiBoundary:
    for feature in outLayer:
      outMultipolygon = ogr.Geometry(ogr.wkbMultiPolygon)
      inMultiPolygon = feature.GetGeometryRef()
      for polygon in inMultiPolygon:
        overlap = boundary.Intersection(polygon)
        if 'POLYGON' in overlap.ExportToWkt():
          overlap.Transform(transform)
          outMultipolygon.AddGeometry(overlap)

  ### Save intersection polygon in memory
  spatialRef = osr.SpatialReference()
  spatialRef.ImportFromEPSG(imageEPSG)
  memDriver = ogr.GetDriverByName('Memory')
  outVector = memDriver.CreateDataSource('mem')
  outLayer = outVector.CreateLayer('', spatialRef, ogr.wkbMultiPolygon)
  outLayer.CreateField(ogr.FieldDefn('id', ogr.OFTInteger))
  definition = outLayer.GetLayerDefn()
  outFeature = ogr.Feature(definition)
  outFeature.SetField('id', 0)
  geometry = ogr.CreateGeometryFromWkb(outMultipolygon.ExportToWkb())
  outFeature.SetGeometry(geometry)
  outLayer.CreateFeature(outFeature)
  outFeature = None

  ### Calculate extent
  (aoiMinX, aoiMaxX, aoiMinY, aoiMaxY) = outLayer.GetExtent()
  aoiLines = int(np.rint((aoiMaxY - aoiMinY)/posting))
  aoiSamples = int(np.rint((aoiMaxX - aoiMinX)/posting))
  maskGeoTrans = (aoiMinX, posting, 0, aoiMaxY, 0, -posting)

  ### Rasterize mask polygon
  gdalDriver = gdal.GetDriverByName('MEM')
  outRaster = gdalDriver.Create('', aoiSamples, aoiLines, 1, gdal.GDT_Float32)
  outRaster.SetGeoTransform((aoiMinX, posting, 0, aoiMaxY, 0, -posting))
  outRaster.SetProjection(outProj.ExportToWkt())
  outBand = outRaster.GetRasterBand(1)
  outBand.SetNoDataValue(0)
  outBand.FlushCache()
  gdal.RasterizeLayer(outRaster, [1], outLayer, burn_values=[1])
  mask = outRaster.GetRasterBand(1).ReadAsArray()
  outVector = None
  outRaster = None

  ### Invert mask (if requested)
  if invert == True:
    mask = 1.0 - mask

  ### Final adjustments
  mask = mask[:dataRows,:dataCols]
  mask[mask==0] = np.nan

  return (mask, maskGeoTrans)


def apply_mask(data, dataGeoTrans, mask, maskGeoTrans):

  (dataRows, dataCols) = data.shape
  dataOriginX = dataGeoTrans[0]
  dataOriginY = dataGeoTrans[3]
  # dataPixelSize = dataGeoTrans[1]
  (maskRows, maskCols) = mask.shape
  maskOriginX = maskGeoTrans[0]
  maskOriginY = maskGeoTrans[3]
  maskPixelSize = maskGeoTrans[1]
  offsetX = int(np.rint((maskOriginX - dataOriginX)/maskPixelSize))
  offsetY = int(np.rint((dataOriginY - maskOriginY)/maskPixelSize))
  data = data[offsetY:maskRows+offsetY,offsetX:maskCols+offsetX]
  data *= mask

  return data


def geotiff2boundary_ext(inGeotiff, maskFile, geographic):

  # Extract metadata
  (spatialRef, gt, shape, pixel) = raster_meta(inGeotiff)
  epsg = int(spatialRef.GetAttrValue('AUTHORITY', 1))
  (data, colFirst, rowsFirst, geoTrans, proj) = \
    geotiff2boundary_mask(inGeotiff, epsg, None)
  (rows, cols) = data.shape

  # Save in mask file (if defined)
  if maskFile is not None:
    gdalDriver = gdal.GetDriverByName('GTiff')
    outRaster = gdalDriver.Create(maskFile, rows, cols, 1, gdal.GDT_Byte)
    outRaster.SetGeoTransform(geoTrans)
    outRaster.SetProjection(proj.ExportToWkt())
    outBand = outRaster.GetRasterBand(1)
    outBand.WriteArray(data)
    outRaster = None

  # Save in memory
  gdalDriver = gdal.GetDriverByName('Mem')
  outRaster = gdalDriver.Create('out', rows, cols, 1, gdal.GDT_Byte)
  outRaster.SetGeoTransform(geoTrans)
  outRaster.SetProjection(proj.ExportToWkt())
  outBand = outRaster.GetRasterBand(1)
  outBand.WriteArray(data)
  data = None

  # Polygonize the raster image
  inBand = outRaster.GetRasterBand(1)
  ogrDriver = ogr.GetDriverByName('Memory')
  outVector = ogrDriver.CreateDataSource('out')
  outLayer = outVector.CreateLayer('boundary', srs=proj)
  fieldDefinition = ogr.FieldDefn('ID', ogr.OFTInteger)
  outLayer.CreateField(fieldDefinition)
  gdal.Polygonize(inBand, inBand, outLayer, 0, [], None)
  outRaster = None

  # Extract geometry from layer
  inSpatialRef = outLayer.GetSpatialRef()
  multipolygon = ogr.Geometry(ogr.wkbMultiPolygon)
  for outFeature in outLayer:
    geometry = outFeature.GetGeometryRef()
    multipolygon.AddGeometry(geometry)
    outFeature = None
  outLayer = None

  # Convert geometry from projected to geographic coordinates (if requested)
  if geographic == True:
    (multipolygon, outSpatialRef) = \
      geometry_proj2geo(multipolygon, inSpatialRef)
    return (multipolygon, outSpatialRef)
  else:
    return (multipolygon, inSpatialRef)


def geotiff2boundary(inGeotiff, maskFile):

  return geotiff2boundary_ext(inGeotiff, maskFile, False)


def geotiff2boundary_geo(inGeotiff, maskFile):

  return geotiff2boundary_ext(inGeotiff, maskFile, True)


# Get polygon for a tile
def get_tile_geometry(tile, step):

  # Extract corners
  xmin = int(tile[1:3])
  ymin = int(tile[4:7])
  if tile[0] == 'S':
    xmin = -xmin
  if tile[3] == 'W':
    ymin = -ymin
  xmax = xmin + step
  ymax = ymin + step

  # Create geometry
  ring = ogr.Geometry(ogr.wkbLinearRing)
  ring.AddPoint_2D(ymax, xmin)
  ring.AddPoint_2D(ymax, xmax)
  ring.AddPoint_2D(ymin, xmax)
  ring.AddPoint_2D(ymin, xmin)
  ring.AddPoint_2D(ymax, xmin)
  polygon = ogr.Geometry(ogr.wkbPolygon)
  polygon.AddGeometry(ring)

  return polygon


# Get tile names
def get_tile_names(minLat, maxLat, minLon, maxLon, step):

  tiles = []
  for i in range(minLon, maxLon, step):
    for k in range(minLat, maxLat, step):
      eastwest = 'W' if i<0 else 'E'
      northsouth = 'S' if k<0 else 'N'
      tile = ('%s%02d%s%03d' % (northsouth, abs(k), eastwest, abs(i)))
      tiles.append(tile)
  return tiles


# Get tiles extent
def get_tiles_extent(tiles, step):

  minLat = 90
  maxLat = -90
  minLon = 180
  maxLon = -180
  for tile in tiles:
    xmin = int(tile[1:3])
    ymin = int(tile[4:7])
    if tile[0] == 'S':
      xmin = -xmin
    if tile[3] == 'W':
      ymin = -ymin
    if xmin < minLat:
      minLat = xmin
    if xmin > maxLat:
      maxLat = xmin
    if ymin < minLon:
      minLon = ymin
    if ymin > maxLon:
      maxLon = ymin
  maxLat += step
  maxLon += step

  return (minLat, maxLat, minLon, maxLon)


# Generate a global tile shapefile
def generate_tile_shape(shapeFile, minLat, maxLat, minLon, maxLon, step):

  # General setup for shapefile
  driver = ogr.GetDriverByName('ESRI Shapefile')
  if os.path.exists(shapeFile):
    driver.DeleteDataSource(shapeFile)
  shapeData = driver.CreateDataSource(shapeFile)

  # Define layer and attributes
  spatialReference = osr.SpatialReference()
  spatialReference.ImportFromEPSG(4326)
  layer = shapeData.CreateLayer(shapeFile, spatialReference, ogr.wkbPolygon)
  fieldname = ogr.FieldDefn('tile', ogr.OFTString)
  fieldname.SetWidth(10)
  layer.CreateField(fieldname)

  # Going through the tiles
  tiles = get_tile_names(minLat, maxLat, minLon, maxLon, step)
  for tile in tiles:
    geometry = get_tile_geometry(tile, step)
    tileGeometry = geometry.ExportToWkt()
    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetField('tile', tile)

    # Define geometry as polygon
    geom = ogr.CreateGeometryFromWkt(tileGeometry)
    if geom:
      feature.SetGeometry(geom)
      layer.CreateFeature(feature)
      feature.Destroy()

  shapeData.Destroy()


# Generate a shapefile from a CSV list file
def list2shape(csvFile, shapeFile):

  # Set up shapefile attributes
  fields = []
  field = {}
  values = []
  field['name'] = 'granule'
  field['type'] = ogr.OFTString
  field['width'] = 254
  fields.append(field)

  files = [line.strip() for line in open(csvFile)]
  for file in files:
    data = gdal.Open(file, GA_ReadOnly)
    if data is not None and data.GetDriver().LongName == 'GeoTIFF':

      print('Reading %s ...' % file)
      # Generate GeoTIFF boundary geometry
      data = None
      (geometry, spatialRef) = geotiff2boundary(file, None)

      # Simplify the geometry - only works with GDAL 1.8.0
      #geometry = geometry.Simplify(float(tolerance))

      # Add granule name and geometry
      base = os.path.basename(file)
      granule = os.path.splitext(base)[0]
      value = {}
      value['granule'] = granule
      value['geometry'] = geometry
      values.append(value)

  # Write geometry to shapefile
  merge = False
  geometry2shape(fields, values, spatialRef, merge, shapeFile)


# Determine the tiles for an area of interest
def aoi2tiles(aoiGeometry):

  # Determine the bounding box
  envelope = aoiGeometry.GetEnvelope()
  west = int(envelope[0] - 0.5)
  east = int(envelope[1] + 1.5)
  south = int(envelope[2] - 0.5)
  north = int(envelope[3] + 1.5)

  # Walk through the potential tiles and add the required on to the geometry
  tiles = []
  multipolygon = ogr.Geometry(ogr.wkbMultiPolygon)
  for i in range(west, east):
    for k in range(south, north):
      eastwest = 'W' if i<0 else 'E'
      northsouth = 'S' if k<0 else 'N'
      tile = ('%s%02d%s%03d' % (northsouth, abs(k), eastwest, abs(i)))
      polygon = get_tile_geometry(tile, 1)
      intersection = polygon.Intersection(aoiGeometry)
      if intersection is not None:
        multipolygon.AddGeometry(polygon)
        tiles.append(tile)

  return (tiles, multipolygon)

def get_latlon_extent(filename):
  src = gdal.Open(filename)
  ulx, xres, xskew, uly, yskew, yres  = src.GetGeoTransform()
  lrx = ulx + (src.RasterXSize * xres)
  lry = uly + (src.RasterYSize * yres)

  source = osr.SpatialReference()
  source.ImportFromWkt(src.GetProjection())

  target = osr.SpatialReference()
  target.ImportFromEPSG(4326)

  transform = osr.CoordinateTransformation(source, target)

  lon1, lat1, h = transform.TransformPoint(ulx, uly)
  lon2, lat2, h = transform.TransformPoint(lrx, uly)
  lon3, lat3, h = transform.TransformPoint(ulx, lry)
  lon4, lat4, h = transform.TransformPoint(lrx, lry)

  lat_min = min(lat1,lat2,lat3,lat4)
  lat_max = max(lat1,lat2,lat3,lat4)
  lon_min = min(lon1,lon2,lon3,lon4)
  lon_max = max(lon1,lon2,lon3,lon4)

  return lat_min, lat_max, lon_min, lon_max

