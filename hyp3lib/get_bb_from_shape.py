from __future__ import print_function, absolute_import, division, unicode_literals

from osgeo import ogr

def get_bb_from_shape(shapeFile):

  # Extract boundary from shapefile
  driver = ogr.GetDriverByName('ESRI Shapefile')
  shape = driver.Open(shapeFile, 0)
  vectorMultipolygon = ogr.Geometry(ogr.wkbMultiPolygon)
  layer = shape.GetLayer()
  # vectorSpatialRef = layer.GetSpatialRef()

  # Reproject polygon if necessary
  # if vectorSpatialRef != rasterSpatialRef:
  #   print('Need to re-project vector polygon')
  #   coordTrans = osr.CoordinateTransformation(vectorSpatialRef, rasterSpatialRef)

  for feature in layer:
    geometry = feature.GetGeometryRef()
    count = geometry.GetGeometryCount()
    if geometry.GetGeometryName() == 'MULTIPOLYGON':
      for i in range(count):
        polygon = geometry.GetGeometryRef(i)
#        if vectorSpatialRef != rasterSpatialRef:
#          polygon.Transform(coordTrans)
        vectorMultipolygon.AddGeometry(polygon)
    else:
#      if vectorSpatialRef != rasterSpatialRef:
#        geometry.Transform(coordTrans)
      vectorMultipolygon.AddGeometry(geometry)
  shape.Destroy()

  envelope = vectorMultipolygon.GetEnvelope()
  minX = envelope[0]
  minY = envelope[2]
  maxX = envelope[1]
  maxY = envelope[3]

  print(minX, minY, maxX, maxY)

  return(minX,minY,maxX,maxY)
