#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from asf_geometry import data2geotiff, geotiff2data
import numpy as np
import logging
import configparser


log = logging.getLogger(__name__)


def tileMask(inFile, maskFile, configFile, outFile):

  ### Read GeoTIFF file
  log.info('Reading GeoTIFF file {0} ...'.format(os.path.basename(inFile)))
  print('Reading GeoTIFF file {0} ...'.format(os.path.basename(inFile)))
  (data, geoTrans, proj, epsg, dtype, noData) = geotiff2data(inFile)
  dataType = dtype
  (rows, cols) = data.shape

  ### Read mask file
  log.info('Reading mask file {0} ...'.format(os.path.basename(maskFile)))
  print('Reading mask file {0} ...'.format(os.path.basename(maskFile)))
  (mask, geoTrans, proj, epsg, dtype, noData) = geotiff2data(maskFile)
  (originX, xPix, xOff, originY, yOff, yPix) = geoTrans

  ### Apply mask
  if dataType == 'BYTE':
    data *= mask.astype(np.uint8)
  elif dataType == 'FLOAT':
    data *= mask.astype(np.float32)

  ### Shrink tile
  config = configparser.ConfigParser(allow_no_value=True)
  config.optionxform = str
  config.read(configFile)
  pixelSize = float(config['Tiles']['pixel size'])
  bufferSize = int(config['Tiles']['buffer'])
  originX += pixelSize*bufferSize
  originY -= pixelSize*bufferSize
  geoTrans = (originX, pixelSize, 0, originY, 0, -pixelSize)
  data = data[bufferSize:rows-bufferSize, bufferSize:cols-bufferSize]

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
  parser.add_argument('configFile', metavar='<config file>',
    help='name of the configuration file for tile parameters')
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

  tileMask(args.inFile, args.maskFile, args.configFile, args.outFile)
