#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from osgeo import gdal, ogr, osr
from asf_time_series import *
from asf_geometry import *


def overlapMaskNetcdf(inFile, maskShape, invert, outFile):

  ### Extract metadata
  meta = nc2meta(inFile)
  xGrid = meta['cols']
  yGrid = meta['rows']
  ntimes = meta['timeCount']
  proj = osr.SpatialReference()
  proj.ImportFromEPSG(meta['epsg'])
  meta['proj'] = proj
  dataGeoTrans = \
    (meta['minX'], meta['pixelSize'], 0, meta['maxY'], 0, -meta['pixelSize'])

  ### Reading time series file
  print('Reading time series file ({0}) ...'.format(inFile))
  dataset = nc.Dataset(inFile, 'r')
  image = dataset.variables['image'][:]
  times = dataset.variables['time'][:]
  granules = dataset.variables['granule'][:]
  dataset.close()

  ### Extract boundary from time series file
  print('Extracting  boundary from time series file ...')
  (meta['boundary'], proj) = netcdf2boundary_mask(inFile, True)

  ### Initialize output file
  initializeNetcdf(outFile, meta)

  ### Generate mask of overlap between image and mask file
  print('Generating overlap mask of image and mask shapefile ({0}) ...'.\
    format(maskShape))
  (mask, maskGeoTrans) = overlapMask(meta, maskShape, invert, outFile)
  ## Set NaNs in mask to zero - assuming we don't have background to worry
  ## about and noise floor is set properly
  mask[np.isnan(mask)] = 0

  ### Apply mask
  print('Applying mask ...')
  for ii in range(ntimes):
    image[ii,:,:] = apply_mask(image[ii,:,:].astype(np.float32),
      dataGeoTrans, mask, maskGeoTrans)

  ### Write masked time series to file
  print('Writing masked time series to file ({0}) ...'.format(outFile))
  dataset = nc.Dataset(outFile, 'a')
  data = dataset.variables['image']
  data[:] = image
  time = dataset.variables['time']
  time[:] = times
  name = dataset.variables['granule']
  name[:] = granules
  dataset.close()


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='overlapMaskGeotiff',
    description='applies a shapefile mask to a netCDF time series file',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('inFile', metavar='<input file>',
    help='name of the netCDF time series input file')
  parser.add_argument('maskShape', metavar='<mask shape>',
    help='name of mask shapefile')
  parser.add_argument('outFile', metavar='<output file>',
    help='name of the masked netCDF time series file')
  parser.add_argument('-invert', action='store_true',
    help='inverting the mask')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.inFile):
    print(' file (%s) does not exist!' % args.inFile)
    sys.exit(1)

  overlapMaskNetcdf(args.inFile, args.maskShape, args.invert, args.outFile)
