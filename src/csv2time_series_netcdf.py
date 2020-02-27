#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import io # To remove that BOM bit from some csv's
import sys
from osgeo import gdal, ogr, osr
from datetime import datetime, timedelta
import netCDF4 as nc
import numpy as np
import configparser
from asf_time_series import addImage2netcdf, initializeNetcdf
from argparse_helpers import file_exists

def csv2time_series_netcdf(csvFile, netcdfFile, days_apart=1):

  ### Read CSV files
  csv_file = io.open(csvFile, "r", encoding='utf-8-sig') # utf-8-sig handles BOM
  lines = [line.rstrip() for line in csv_file]
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
    days = timedelta(days=ii*days_apart)
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
  parser.add_argument('csv', metavar='<csvfile>', action="store", type=file_exists,
    help='name of the CSV input file')
  parser.add_argument('netcdf', metavar='<netCDF file>', action="store",
    help='name of the netCDF test time series output file')
  parser.add_argument('--days','-d', action="store", type=int, default=1,
    help='Number of days apart to save each granule. (Default=1)')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  csv2time_series_netcdf(args.csv, args.netcdf, days_apart=args.days)
