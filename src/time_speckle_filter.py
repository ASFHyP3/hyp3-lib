#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from asf_time_series import *


def time_speckle_filter(inFile, length, step, discrete, outFile):

  ### Extract metadata
  meta = nc2meta(inFile)
  xGrid = meta['cols']
  yGrid = meta['rows']
  ntimes = meta['timeCount']

  ### Determine start and stop indices
  if length % 2 != 1:
    print('Length of time speckle needs to be odd!')
    sys.exit(1)
  start = int(length/2)
  stop = ntimes - start
  timeCount = int((stop - start)/step)
  if discrete == True:
    offset = ntimes - stop
    start = ntimes - timeCount*step + offset

  ### Reading time series
  dataset = nc.Dataset(inFile, 'r')
  image = dataset.variables['image'][:]
  times = dataset.variables['time'][start:stop:step]
  granules = dataset.variables['granule'][start:stop:step]
  dataset.close()

  ### Initialize output file
  meta['timeCount'] = timeCount
  initializeNetcdf(outFile, meta)

  ### Applying median filter
  filtered = np.full((meta['timeCount'], meta['rows'], meta['cols']), np.nan)
  indices = np.arange(start, stop, step)
  for ii in indices:
    index = int((ii - indices[0])/step)
    filtered[index,:,:] = np.median(image[ii-start:ii-start+length,:,:],
      axis=0)

  ### Write filtered time series to file
  dataset = nc.Dataset(outFile, 'a')
  data = dataset.variables['image']
  data[:] = filtered
  time = dataset.variables['time']
  time[:] = times
  name = dataset.variables['granule']
  name[:] = granules
  dataset.close()


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='time_speckle_filter',
    description='filters the speckle out of a time series',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('inFile', metavar='<input file>',
    help='name of the netCDF time series file')
  parser.add_argument('-length', metavar='<filter length>',
    help='length of time speckle filter in time (default 3)', default=3)
  parser.add_argument('-discrete', action='store_true',
    help='use the time filter discretely (no overlaps)')
  parser.add_argument('outFile', metavar='<output file>',
    help='name of the detrended netCDF time series file')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.inFile):
    print('netCDF file (%s) does not exist!' % args.inFile)
    sys.exit(1)

  step = 1
  if args.discrete == True:
    step = int(args.length)
  time_speckle_filter(args.inFile, int(args.length), step, args.discrete, 
    args.outFile)
