#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from asf_time_series import time_series_slice
import matplotlib.pyplot as plt
import numpy as np


def time_series_profile(ncFile, line, sample, outBase):

  ### Extract time series slice
  (granule, time, value) = time_series_slice(ncFile, sample, line)
  count = len(granule)
  x = np.arange(count)

  ### Write profile to CSV file
  outFile = outBase + '_profile.csv'
  with open(outFile, 'w') as outF:
    outF.write('granule,time,value\n')
    for ii in range(count):
      out = ('{0},{1},{2}\n'.format(granule[ii], time[ii], value[ii]))
      outF.write(out.replace('nan',''))

  ### Stats
  minValue = np.nanmin(value)
  maxValue = np.nanmax(value)
  meanValue = np.nanmean(value)
  stdValue = np.nanstd(value)
  outFile = outBase + '_stats.csv'
  with open(outFile, 'w') as outF:
    outF.write('minimum,maximum,mean,standard deviation\n')
    outF.write('%.12f,%.12f,%.12f,%.12f\n' % (minValue, maxValue, meanValue,
      stdValue))
  print('minimum: %.12f' % minValue)
  print('maximum: %.12f' % maxValue)
  print('mean: %.12f' % meanValue)
  print('stdev: %.12f' % stdValue)

  ### Plot profile
  outFile = outBase + '_profile.png'
  plt.figure(figsize=(8,6))
  plt.xlabel('Time')
  plt.xticks(x, time, rotation='vertical')
  plt.subplots_adjust(bottom=0.25)
  plt.ylabel('Pixel value')
  plt.title('Time series profile (line: {0}, sample: {1})'.format(line,sample))
  plt.grid(True)
  plt.plot(x, value)
  plt.savefig(outFile, dpi=300)
  fig = None


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='time_series_profile',
    description='extracts a netCDF time series slice and saves results',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('inFile', metavar='<netCDF file>',
    help='name of the netCDF time series file')
  parser.add_argument('line', metavar='<line>',
    help='line of pixel for time series')
  parser.add_argument('sample', metavar='<sample>',
    help='sample of pixel for time series')
  parser.add_argument('outFile', metavar='<output file>',
    help='basename of the output file')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.inFile):
    print('netCDF file (%s) does not exist!' % args.inFile)
    sys.exit(1)

  time_series_profile(args.inFile, int(args.line), int(args.sample),
    args.outFile)
