#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from asf_time_series import *
from statsmodels.tsa.seasonal import seasonal_decompose
import statsmodels.api as sm
import time as ti
import matplotlib.pyplot as plt
import logging

# stub logger
log = logging.getLogger(__name__)


def time_series_trend(inFile, outFile):

  ### Reading time series
  log.info('Removing trend from {0} ...'.format(inFile))
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

  ### Looping over image dimensions
  for x in range(xGrid):
    first = ti.time()
    for y in range(yGrid):

      mean = np.mean(image[:,y,x])
      if np.isfinite(mean) == True and mean > 0:

        ## Smoothing the time line with localized regression (LOESS)
        lowess = sm.nonparametric.lowess
        smooth = lowess(image[:,y,x], np.arange(ntimes), frac=0.08, it=0)[:,1]

        ## Remove trend from time series slice
        sd = seasonal_decompose(x=smooth, model='additive', freq=4)
        residuals = sd.resid
        residuals[np.isnan(residuals)] = 0.0
        image[:,y,x] = residuals

      else:
        image[:,y,x] = mean

    last = ti.time()
    log.info('loop %4d: %.3lf' % (x, last-first))

  ### Write residuals to file
  dataset = nc.Dataset(outFile, 'a')
  data = dataset.variables['image']
  data[:] = image
  time = dataset.variables['time']
  time[:] = times
  name = dataset.variables['granule']
  name[:] = granules
  dataset.close()


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='time_series_trend',
    description='removes trend from netCDF time series',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('inFile', metavar='<input file>',
    help='name of the netCDF time series file')
  parser.add_argument('outFile', metavar='<output file>',
    help='name of the detrended netCDF time series file')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  # configure logging
  log = logging.getLogger()

  if not os.path.exists(args.inFile):
    log.error('netCDF file (%s) does not exist!' % args.inFile)
    sys.exit(1)

  time_series_trend(args.inFile, args.outFile)
