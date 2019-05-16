#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from osgeo import gdal, ogr, osr
from asf_time_series import *
from asf_geometry import *


def overlapMaskGeotiff(inFile, maskShape, invert, outFile):

  ### Read data from GeoTIFF file
  (data, dataGeoTrans, proj, imageEPSG, dtype, noData) = geotiff2data(inFile)
  posting = dataGeoTrans[1]

  ### Determine GeoTIFF boundary polygon in geographic coordinates
  print('Determining GeoTIFF ({0}) boundary polygon ...'.format(inFile))
  (multiBoundary, spatialRef) = geotiff2boundary_geo(inFile, None)

  ### Generate mask of overlap between image and mask file
  print('Generating overlap mask of image and mask shapefile ({0})...'.\
    format(maskShape))
  meta = {}
  meta['pixelSize'] = dataGeoTrans[1]
  meta['proj'] = proj
  meta['epsg'] = imageEPSG
  meta['boundary'] = multiBoundary
  (dataRows, dataCols) = data.shape
  meta['rows'] = dataRows
  meta['cols'] = dataCols
  (mask, maskGeoTrans) = overlapMask(meta, maskShape, invert, outFile)

  ### Apply mask
  print('Applying mask ...')
  data = apply_mask(data.astype(np.float32), dataGeoTrans, mask, maskGeoTrans)

  ### Save mask into GeoTIFF file
  print('Saving result to GeoTIFF file ({0})'.format(outFile))
  data2geotiff(data, dataGeoTrans, proj, 'FLOAT', 0, outFile)


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='overlapMaskGeotiff',
    description='applies a shapefile mask to a GeoTIFF file',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('inFile', metavar='<input file>',
    help='name of the overlap GeoTIFF input file')
  parser.add_argument('maskShape', metavar='<mask shape>',
    help='name of mask shapefile')
  parser.add_argument('outFile', metavar='<output file>',
    help='name of the masked GeoTIFF output file')
  parser.add_argument('-invert', action='store_true',
    help='inverting the mask')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.inFile):
    print(' file (%s) does not exist!' % args.inFile)
    sys.exit(1)

  overlapMaskGeotiff(args.inFile, args.maskShape, args.invert, args.outFile)
