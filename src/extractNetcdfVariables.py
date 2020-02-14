#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from osgeo import ogr, osr
from asf_time_series import extractNetcdfTime, extractNetcdfGranule


def extractNetcdfVariable(ncFile, variable, outFile):

  if variable.upper() == 'TIME':
    print('Extracting time information from {0}' \
      .format(os.path.basename(ncFile)))
    extractNetcdfTime(ncFile, outFile)
  elif variable.upper() == 'GRANULE':
    print('Extracting granule information from {0}' \
      .format(os.path.basename(outFile)))
    extractNetcdfGranule(ncFile, outFile)


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='extractNetcdfVariables',
    description='extract variable information from netCDF file',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('netcdf', metavar='<netCDF file>',
    help='name of the netCDF list')
  parser.add_argument('variable', metavar='<variable>',
    help='name of the variable for which information is extracted')
  parser.add_argument('outfile', metavar='<csv file>',
    help='name of the output file')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.netcdf):
    print('File list (%s) does not exist!' % args.netcdf)
    sys.exit(1)

  extractNetcdfVariable(args.netcdf, args.variable, args.outfile)
