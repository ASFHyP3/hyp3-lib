#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
import h5py
from asf_time_series import *


def filterChangeNetcdf(inFile, size, iter, outFile):

  ### Reading time series
  print('Reading time series ...')
  meta = nc2meta(inFile)
  dataset = nc.Dataset(inFile, 'r')
  xGrid = meta['cols']
  yGrid = meta['rows']
  ntimes = meta['timeCount']
  image = dataset.variables['image'][:]
  times = dataset.variables['time'][:]
  granules = dataset.variables['granule'][:]
  dataset.close()

  ### Initialize output file
  initializeNetcdf(outFile, meta)

  ### Morphological filter
  print('Applying morphological filter ...')
  kernelSize = (int(size),int(size))
  iterations = int(iter)
  for t in range(ntimes):
    image[t,:,:] = filter_change(image[t,:,:], kernelSize, iterations)

  ### Write filtered image stack to file
  print('Writing filtered image stack to file ...')
  dataset = nc.Dataset(outFile, 'a')
  data = dataset.variables['image']
  data[:] = image
  time = dataset.variables['time']
  time[:] = times
  name = dataset.variables['granule']
  name[:] = granules
  dataset.close()


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='filterChangeNetcdf',
    description='filters a change detection time series netCDF file using a ' \
      'morphological filter',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('inFile', metavar='<input file>',
    help='name of the unfiltered input file')
  parser.add_argument('-size', metavar='<kernel size>',
    help='size of filter kernel in pixels (default: 5)', default=5)
  parser.add_argument('-iter', metavar='<iterations>',
    help='number of iterations for filtering (default: 1)', default=1)
  parser.add_argument('outFile', metavar='<output file>',
    help='name of the filtered output file')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.inFile):
    print('Matlab file (%s) does not exist!' % args.inFile)
    sys.exit(1)

  filterChangeNetcdf(args.inFile, args.size, args.iter, args.outFile)
