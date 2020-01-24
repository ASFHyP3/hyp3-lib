#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from osgeo import ogr, osr
import numpy as np
from asf_geometry import shape2geometry_ext, geometry2shape


def commonOverlapBoundary(listFile, granuleDir, granuleFile, shapeFile):

  area = []
  geometry = []
  files = [line.strip() for line in open(listFile)]
  fileCount = len(files)

  # Extract areas and geometries from boundary shapefiles
  for fileName in files:
    (fields, values, spatialRef) = shape2geometry_ext(fileName)
    epsg = np.int(values[0]['epsg'])
    pixSize = np.float(values[0]['pixSize'])
    pixel = values[0]['pixel']
    area.append(float(values[0]['area']))
    multiPolygon = values[0]['geometry']
    for polygon in multiPolygon:
      geometry.append(polygon.ExportToWkt())

  # Determine the list of granules to consider - overlap > 90 %
  print('Forming intersections of all geometries ...')
  index = []
  for ii in range(fileCount):
    print('Intersections with %s ...' % os.path.basename(files[ii]))
    for kk in range(fileCount):
      if ii < kk:
        poly1 = ogr.CreateGeometryFromWkt(geometry[ii])
        poly2 = ogr.CreateGeometryFromWkt(geometry[kk])
        meanArea = (area[ii] + area[kk])/2.0
        intersection = poly1.Intersection(poly2)
        intersectArea = intersection.GetArea()
        overlap = intersectArea/meanArea
        if overlap > 0.9:
          index.append(ii)
          index.append(kk)
  index = list(set(index))

  # Write common overlap granules to list file
  fp = open(granuleFile, 'w')
  for ii in range(len(index)):
    fp.write('%s\n' % os.path.join(granuleDir,
      os.path.basename(files[index[ii]]).replace('_boundary.shp','.tif')))
  fp.close()

  # Set up shapefile attributes
  values = []
  value = {}
  spatialRef = osr.SpatialReference()
  spatialRef.ImportFromEPSG(epsg)

  # Generate common overlap
  intersection = ogr.CreateGeometryFromWkt(geometry[index[0]])
  for ii in range(1, len(index)):
    poly = ogr.CreateGeometryFromWkt(geometry[index[ii]])
    intersection = poly.Intersection(intersection)
  for geometry in intersection:
    geomWkt = geometry.ExportToWkt()
    if 'POLYGON' in geomWkt or 'LINEARRING' in geomWkt:
      if 'POLYGON' in geomWkt:
        polygon = geometry
      elif 'LINEARRING' in geomWkt:
        polygon = ogr.Geometry(ogr.wkbPolygon)
        polygon.AddGeometry(geometry)
      envelope = geometry.GetEnvelope()
      area = geometry.GetArea()
      centroid = geometry.Centroid().ExportToWkt()
      value['value'] = 1
      value['granule'] = 'common overlap'
      value['epsg'] = epsg
      value['originX'] = envelope[0]
      value['originY'] = envelope[3]
      value['pixSize'] = pixSize
      value['cols'] = np.int(np.rint((envelope[1] - envelope[0])/pixSize))
      value['rows'] = np.int(np.rint((envelope[3] - envelope[2])/pixSize))
      value['pixel'] = pixel
      value['area'] = area
      value['geometry'] = polygon
      value['centroid'] = centroid
      values.append(value)

  # Write geometry to shapefile
  geometry2shape(fields, values, spatialRef, False, shapeFile)


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='commonOverlapBoundary',
    description='generates a common overlap shapefile from a list of boundary '\
    'shapefiles', formatter_class=RawTextHelpFormatter)
  parser.add_argument('input', metavar='<file list>',
    help='name of the boundary shapefile list')
  parser.add_argument('granules', metavar='<granules list>',
    help='name of the common overlap granule list')
  parser.add_argument('shape', metavar='<shape file>',
    help='name of the common overlap shapefile')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.input):
    print('File list (%s) does not exist!' % args.input)
    sys.exit(1)

  commonOverlapBoundary(args.input, args.granules, args.shape)
