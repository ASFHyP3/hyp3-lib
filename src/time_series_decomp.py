#!/usr/bin/python

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from asf_time_series import *
import matplotlib.pyplot as plt


def time_series2csv(ncFile, x, y, typeXY, outBase):

  ### Extract time series slice
  (granule, time, index, value, sd) = \
    time_series_slice(ncFile, x, y, typeXY)
  count = len(granule)

  ### Write list to CSV file
  outFile = outBase + '_decomp.csv'
  with open(outFile, 'wb') as csv:
    csv.write('granule,time,value,seasonalAdd,trendAdd,residualAdd\n')
    for ii in range(count):
      out = ('{0},{1},{2},{3},{4},{5}\n'.format(granule[ii],
        time[ii], value[ii], sd.seasonal[ii], sd.trend[ii], sd.resid[ii]))
      csv.write(out.replace('nan',''))

  ### Plot additivie decomposition
  outFile = outBase + '_additive.png'
  fig, axes = plt.subplots(4, 1, sharex=True, sharey=False)
  fig.set_figheight(10)
  fig.set_figwidth(15)
  axes[0].set_title('Additive Time Series')
  axes[0].plot(time, value, 'k')
  axes[0].set_ylabel('original')
  axes[1].plot(time, sdAdd.trend)
  axes[1].set_ylabel('trend')
  axes[2].plot(time, sdAdd.seasonal, 'g')
  axes[2].set_ylabel('seasonal')
  axes[3].plot(time, sdAdd.resid, 'r')
  axes[3].set_ylabel('residual')
  plt.savefig(outFile, dpi=300)
  fig = None

  '''
  ### Plot multiplicative decomposition
  outFile = outBase + '_multiplicative.png'
  fig, axes = plt.subplots(4, 1, sharex=True, sharey=False)
  fig.set_figheight(10)
  fig.set_figwidth(15)
  axes[0].set_title('Multiplicative Time Series')
  axes[0].plot(time, value, 'k')
  axes[0].set_ylabel('original')
  axes[1].plot(time, sdMult.trend)
  axes[1].set_ylabel('trend')
  axes[2].plot(time, sdMult.seasonal, 'g')
  axes[2].set_ylabel('seasonal')
  axes[3].plot(time, sdMult.resid, 'r')
  axes[3].set_ylabel('residual')
  plt.savefig(outFile, dpi=300)
  fig = None
  '''


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='time_series_decomp',
    description='decomposes netCDF time series slice and saves results',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('inFile', metavar='<netCDF file>',
    help='name of the netCDF time series file')
  parser.add_argument('outFile', metavar='<output file>',
    help='basename of the output file')
  pixel = parser.add_mutually_exclusive_group(required=True)
  pixel.add_argument('-pixel', metavar=('<line>','<sample>'), nargs=2,
    default=None, help='line and sample of pixel for time series')
  pixel.add_argument('-latlon', metavar=('<lat>','<lon>'), nargs=2,
    default=None, help='latitude and longitude of pixel for time series')
  pixel.add_argument('-mapXY', metavar=('<xGrid>','<yGrid>'), nargs=2,
    default=None, help='x and y coordinate of pixel for time series')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.inFile):
    print('netCDF file (%s) does not exist!' % args.inFile)
    sys.exit(1)

  if args.pixel != None:
    (y, x) = args.pixel
    typeXY = 'pixel'
  elif args.latlon != None:
    (y, x) = args.latlon
    typeXY = 'latlon'
  elif args.mapXY != None:
    (x, y) = args.mapXY
    typeXY = 'mapXY'
  time_series2csv(args.inFile, float(x), float(y), typeXY, args.outFile)
