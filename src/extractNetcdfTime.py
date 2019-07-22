#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from datetime import datetime, timedelta
from asf_time_series import *
import logging

# stub logger
log = logging.getLogger(__name__)


def extractNetcdfTime(ncFile, csvFile):

  outF = open(csvFile, 'w')
  timeSeries = nc.Dataset(ncFile, 'r')
  timeRef = timeSeries.variables['time'].getncattr('units')[14:]
  timeRef = datetime.strptime(timeRef, '%Y-%m-%d %H:%M:%S')
  time = timeSeries.variables['time'][:].tolist()
  for t in time:
    timestamp = timeRef + timedelta(seconds=t)
    outF.write('%s\n' % timestamp.isoformat())
  outF.close()


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='extractNetcdfTime',
    description='extracts time information from netCDF and saves to file',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('inFile', metavar='<input file>',
    help='name of the netCDF time series file')
  parser.add_argument('outFile', metavar='<output file>',
    help='name of the output CSV file')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  # configure logging
  log = logging.getLogger()

  if not os.path.exists(args.inFile):
    log.error('NetCDF file (%s) does not exist!' % args.inFile)
    sys.exit(1)

  extractNetcdfTime(args.inFile, args.outFile)
