#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from asf_time_series import time_series_slice
import numpy as np
import netCDF4 as nc


def time_series_layer_stats(ncFile):

  timeSeries = nc.Dataset(ncFile, 'r')

  ### Extract information for variables: image, granule
  granules = timeSeries.variables['granule']
  granule = nc.chartostring(granules[:])
  data = timeSeries.variables['image']
  numLayers = len(granule)

  ### Calculate statistics
  minimum = []
  maximum = []
  mean = []
  stdev = []
  for ii in range(numLayers):

    value = data[ii,:,:]
    maximum.append(np.nanmax(value))
    minimum.append(np.nanmin(value))
    mean.append(np.nanmean(value))
    stdev.append(np.nanstd(value))

  return (granule, minimum, maximum, mean, stdev)


def time_series_stats(ncFile, outFile):

  print('time series: %s' % os.path.basename(ncFile))

  ### Calculate statistics for time series
  (granule, minimum, maximum, mean, stdev) = time_series_layer_stats(ncFile)
  numLayers = len(minimum)

  ### Write statistics to CSV file
  outF = open(outFile, 'w')
  outF.write('Granule,Minimum,Maximum,Mean,Stdev\n')
  for ii in range(numLayers):

    print('\ngranule: %s' % granule[ii])
    print('minimum: %.12f' % minimum[ii])
    print('maximum: %.12f' % maximum[ii])
    print('mean: %.12f' % mean[ii])
    print('stdev: %.12f' % stdev[ii])

    outF.write('%s,%.12f,%.12f,%.12f,%.12f\n' % (os.path.basename(granule[ii]),
      minimum[ii], maximum[ii], mean[ii], stdev[ii]))
  outF.close()


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='time_series_layer_stats',
    description='calculate stats for netCDF time series layers and saves results',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('inFile', metavar='<netCDF file>',
    help='name of the netCDF time series file')
  parser.add_argument('outFile', metavar='<output file>',
    help='name of the CSV file')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.inFile):
    print('netCDF file (%s) does not exist!' % args.inFile)
    sys.exit(1)

  time_series_stats(args.inFile, args.outFile)
