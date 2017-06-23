#!/usr/bin/python

import os
import sys
from osgeo import gdal, ogr, osr
from scipy import ndimage
import numpy as np
from osgeo.gdalconst import GA_ReadOnly


# Determine the boundary polygon of a GeoTIFF file
def geotiff2polygon(geotiff):

  raster = gdal.Open(geotiff)
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

  return polygon


def geotiff_overlap(firstFile, secondFile, type):

  # Check map projections
  raster = gdal.Open(firstFile)
  proj = raster.GetProjection()
  gt = raster.GetGeoTransform()
  pixelSize = gt[1]
  raster = None

  # Extract boundary polygons
  firstPolygon = geotiff2polygon(firstFile)
  secondPolygon = geotiff2polygon(secondFile)

  if type == 'intersection':
    overlap = firstPolygon.Intersection(secondPolygon)
  elif type == 'union':
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
    log.error('Could not extract information (tile) out of shapefile (%s)' %
      reference)
    sys.exit(1)
  (boundary, spatialRef, granule) = shape2geometry(source, 'granule')
  if boundary is None:
    log.error('Could not extract information (granule) out of shapefile (%s)' %
      source)
    sys.exit(1)

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


# Extract boundary of GeoTIFF file into geometry with geographic coordinates
def geotiff2boundary(inGeotiff):

  # Generating a mask for the GeoTIFF
  inRaster = gdal.Open(inGeotiff)
  geoTrans = inRaster.GetGeoTransform()
  proj = osr.SpatialReference()
  proj.ImportFromWkt(inRaster.GetProjectionRef())
  inBand = inRaster.GetRasterBand(1)
  data = inBand.ReadAsArray()
  [cols, rows] = data.shape
  data[data>0] = 1
  data = ndimage.binary_closing(data, iterations=10,
    structure=np.ones((3,3))).astype(data.dtype)
  gdalDriver = gdal.GetDriverByName('Mem')
  outRaster = gdalDriver.Create('out', rows, cols, 1, gdal.GDT_Byte)
  outRaster.SetGeoTransform(geoTrans)
  outRaster.SetProjection(proj.ExportToWkt())
  outBand = outRaster.GetRasterBand(1)
  outBand.WriteArray(data)
  inBand = None
  inRaster = None
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

  # Convert geometry from projected to geographic coordinates
  (multipolygon, outSpatialRef) = geometry_proj2geo(multipolygon, inSpatialRef)

  return (multipolygon, outSpatialRef)


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
      (geometry, spatialRef) = geotiff2boundary(file)

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
