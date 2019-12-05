#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from asf_geometry import data2geotiff, geotiff2data
from asf_time_series import nc2meta, initializeNetcdf
from osgeo import osr
import netCDF4 as nc
import numpy as np
import logging


log = logging.getLogger(__name__)


def tileMask(inFile, maskFile, outFile):

  ### Read GeoTIFF file
  log.info('Reading GeoTIFF file {0} ...'.format(os.path.basename(inFile)))
  print('Reading GeoTIFF file {0} ...'.format(os.path.basename(inFile)))
  (data, geoTrans, proj, epsg, dtype, noData) = geotiff2data(inFile)
  dataType = dtype

  ### Read mask file
  log.info('Reading mask file {0} ...'.format(os.path.basename(maskFile)))
  print('Reading mask file {0} ...'.format(os.path.basename(maskFile)))
  (mask, geoTrans, proj, epsg, dtype, noData) = geotiff2data(maskFile)

  ### Apply mask
  if dataType == 'BYTE':
    data *= mask.astype(np.uint8)
  elif dataType == 'FLOAT':
    data *= mask.astype(np.float32)

  ### Write GeoTIFF to file
  log.info('Writing GeoTIFF file to {0} ...'.format(os.path.basename(outFile)))
  print('Writing GeoTIFF file to {0} ...'.format(os.path.basename(outFile)))
  data2geotiff(data, geoTrans, proj, dataType, -1.0, outFile)


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='tileMask',
    description='Apply mask to GeoTIFF file',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('inFile', metavar='<input file>',
    help='name of the input GeoTIFF file')
  parser.add_argument('maskFile', metavar='<mask file>',
    help='name of the mask file')
  parser.add_argument('outFile', metavar='<output file>',
    help='name of the output GeoTIFF file')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.inFile):
    print('GeoTIFF file (%s) does not exist!' % args.inFile)
    sys.exit(1)
  if not os.path.exists(args.maskFile):
    print('Mask file (%s) does not exist!' % args.maskFile)
    sys.exit(1)

  tileMask(args.inFile, args.maskFile, args.outFile)
