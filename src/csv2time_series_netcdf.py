#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from osgeo import gdal, ogr, osr
from datetime import datetime, timedelta
import netCDF4 as nc
import numpy as np
import configparser
from asf_time_series import addImage2netcdf, initializeNetcdf


def csv2time_series_netcdf(csvFile, netcdfFile):

  ### Read CSV files
  lines = [line.rstrip() for line in open(csvFile)]
  timeCount = len(lines)
  width = len(lines[0].split(','))
  height = 1
  print('Reading CSV file ({0}) ...'.format(os.path.basename(csvFile)))
  print(' Found {0} time counts and {1} columns'.format(timeCount, width))

  ### Make some alternative metadata
  meta = {}
  meta['institution'] = 'Alaska Satellite Facility'
  meta['title'] = 'Time series test'
  meta['source'] = 'Set of made up time series values'
  meta['comment'] = 'No guarantees are made. Use at your own risk.'
  meta['reference'] = 'Greetings from the testing department.'
  meta['imgLongName'] = 'powerscale'
  meta['imgUnits'] = 'none'
  meta['imgNoData'] = np.nan
  minX = 465704
  maxY = 7191221
  posting = 10.0
  meta['epsg'] = 32606
  meta['minX'] = minX
  meta['maxX'] = minX + posting*width
  meta['minY'] = maxY - posting*height
  meta['maxY'] = maxY
  meta['cols'] = width
  meta['rows'] = height
  meta['pixelSize'] = posting
  refTimestamp = '2020-01-01 12:00:00'
  meta['refTime'] = refTimestamp

  ### Make up granule names and timestamps
  granule = []
  timestamp = []
  refTime = datetime.strptime(refTimestamp, '%Y-%m-%d %H:%M:%S')
  for ii in range(timeCount):
    layerName = ('test_layer_%03d' % (ii+1))
    granule.append(layerName)
    days = timedelta(days=ii)
    date = refTime + days
    #timestamp.append(datetime.strptime(date, '%Y%m%dT%H%M%S'))
    timestamp.append(date)

  ### Generate nedCDF time series file
  print('Generate netCDF test time series file ({0}) ...' \
    .format(os.path.basename(netcdfFile)))

  initializeNetcdf(netcdfFile, meta)

  ### Fill in all time slices
  for ii in range(timeCount):
    values = lines[ii].split(',')
    data = np.array(values)
    addImage2netcdf(data, netcdfFile, granule[ii], timestamp[ii])
    data = None


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='csv2time_series_file',
    description='generates a time series stack from a CSV file',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('csv', metavar='<csvfile>',
    help='name of the CSV input file')
  parser.add_argument('netcdf', metavar='<netCDF file>',
    help='name of the netCDF test time series file')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.csv):
    print('Configuration file (%s) does not exist!' % args.config)
    sys.exit(1)

  csv2time_series_netcdf(args.csv, args.netcdf)
