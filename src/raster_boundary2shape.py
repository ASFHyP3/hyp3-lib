#!/usr/bin/python
import argparse
from argparse import RawTextHelpFormatter
import os
from osgeo import gdal, ogr, osr
import sys
from asf_geometry import *

# from asf_time_series import raster_metadata
 
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


def raster_boundary2shape(inFile, threshold, outShapeFile):
    # Extract raster image metadata
    print('Extracting raster information ...')
    (fields, values, spatialRef) = raster_metadata(inFile)
    if spatialRef.GetAttrValue('AUTHORITY', 0) == 'EPSG':
        epsg = int(spatialRef.GetAttrValue('AUTHORITY', 1))
    # Generate GeoTIFF boundary geometry
    print('Extracting boundary geometry ...')
    (data, colFirst, rowFirst, geoTrans, proj) = \
        geotiff2boundary_mask(inFile, epsg, threshold)
    (rows, cols) = data.shape
    values[0]['originX'] = geoTrans[0]
    values[0]['originY'] = geoTrans[3]
    values[0]['rows'] = rows
    values[0]['cols'] = cols

    # Write broundary to shapefile
    print('Writing boundary to shapefile ...')
    data_geometry2shape(data, fields, values, spatialRef, geoTrans, outShapeFile)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='raster_boundary2shape',
             description='generates boundary shapefile from GeoTIFF file',
             formatter_class=RawTextHelpFormatter)
    parser.add_argument('input', metavar='<geotiff file>',
             help='name of the GeoTIFF file')
    parser.add_argument('-threshold', metavar='<code>', action='store',
             default=None, help='threshold value what is considered blackfill')
    parser.add_argument('shape', metavar='<shape file>',
             help='name of the shapefile')
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print('GeoTIFF file (%s) does not exist!' % args.input)
        sys.exit(1)

    raster_boundary2shape(args.input, args.threshold, args.shape)


