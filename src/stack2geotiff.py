#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from osgeo import gdal, ogr, osr
import netCDF4 as nc
from asf_geometry import data2geotiff
from asf_time_series import nc2meta
from statsStackResults import ncStack2meta


def stack2geotiff(ncFile, outDir):

  ### Set up output directory (if needed)
  if not os.path.exists(outDir):
    os.makedirs(outDir)

  ### Read time series data - confidence level
  print('Reading confidence level from time series file ({0}) ...' \
    .format(os.path.basename(ncFile)))
  meta = ncStack2meta(ncFile)
  dataset = nc.Dataset(ncFile, 'r')
  confidenceLevel = dataset.variables['confidenceLevel'][:]
  dataset.close()

  spatialRef = osr.SpatialReference()
  spatialRef.ImportFromEPSG(meta['epsg'])
  geoTrans = ( meta['minX'], meta['pixelSize'], 0, meta['maxY'], 0,
    -meta['pixelSize'])

  ### Convert confidence level layers to GeoTIFF
  for ii in range(meta['stackCount']):
    outFile = os.path.join(outDir, 'confidenceLevel_{0}.tif'.format(ii+1))
    print('Saving confidence level to GeoTIFF file ({0})' \
      .format(os.path.basename(outFile)))
    data = confidenceLevel[ii,:,:]
    data2geotiff(data, geoTrans, spatialRef, 'FLOAT', 0, outFile)

  confidenceLevel = None


  ### Read time series data - change start time
  print('Reading change start time from time series file ({0}) ...' \
    .format(os.path.basename(ncFile)))
  dataset = nc.Dataset(ncFile, 'r')
  changeStartTime = dataset.variables['changeStartTime'][:]
  dataset.close()

  ### Convert change start time layers to GeoTIFF
  for ii in range(meta['stackCount']):
    outFile = os.path.join(outDir, 'changeStartTime_{0}.tif'.format(ii+1))
    print('Saving change start time to GeoTIFF file ({0})' \
      .format(os.path.basename(outFile)))
    data = changeStartTime[ii,:,:]
    data2geotiff(data, geoTrans, spatialRef, 'FLOAT', 0, outFile)

  changeStartTime = None


  ### Read time series data - change stop time
  print('Reading change stop time from time series file ({0}) ...' \
    .format(os.path.basename(ncFile)))
  dataset = nc.Dataset(ncFile, 'r')
  changeStopTime = dataset.variables['changeStopTime'][:]
  dataset.close()

  ### Convert change start time layers to GeoTIFF
  for ii in range(meta['stackCount']):
    outFile = os.path.join(outDir, 'changeStopTime_{0}.tif'.format(ii+1))
    print('Saving change stop time to GeoTIFF file ({0})' \
      .format(os.path.basename(outFile)))
    data = changeStopTime[ii,:,:]
    data2geotiff(data, geoTrans, spatialRef, 'FLOAT', 0, outFile)

  changeStopTime = None


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='stack2geotiff',
    description='extracts stack layers and stores them in GeoTIFF format',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('inFile', metavar='<input file>',
    help='name of the netCDF time series file')
  parser.add_argument('outDir', metavar='<output directory>',
    help='name of the output directory')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.inFile):
    print('netCDF file (%s) does not exist!' % args.inFile)
    sys.exit(1)

  stack2geotiff(args.inFile, args.outDir)
