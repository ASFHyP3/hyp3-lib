#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from osgeo import gdal, ogr, osr
import netCDF4 as nc
import numpy as np
from asf_geometry import data2geotiff
from asf_time_series import ncStream2meta, getNetcdfGranule
from argparse_helpers import file_exists, dir_exists_create


# ncFilePath = str path to nc.Dataset, or Dataset itself
# outDir = str path
# granuleList = list[str]
def time_series2geotiff(ncFile, outDir, granuleList=None):
  # Doublecheck outDir, incase called from another script:
  outDir = dir_exists_create(outDir)
  # If you pass a path, vs passing the file itself:
  if isinstance(ncFile, str):
    dataset = nc.Dataset(ncFile, 'r')
    opened_file = True
  else:
    dataset = ncFile
    opened_file = False

  if granuleList == None:
    granuleList = getNetcdfGranule(dataset)

  ### Read time series data
  images = dataset.variables['image'][:]
  
  ### Read time series metadata and
  meta = ncStream2meta(dataset)
  spatialRef = osr.SpatialReference()
  spatialRef.ImportFromEPSG(meta['epsg'])
  geoTrans = ( meta['minX'], meta['pixelSize'], 0, meta['maxY'], 0, -meta['pixelSize'])

  geotiff_paths = []
  ### Go through granuleList
  for granule in granuleList:
    ## Determine index of the granule in the time series
    t = granuleList.index(granule)
    data = images[t,:,:]
    outFile = os.path.join(outDir, granule+'_time_series.tif')
    geotiff_paths.append(outFile)

    ## Save time series layers into GeoTIFF files
    print('Saving result to GeoTIFF file ({0})'.format(outFile))
    data2geotiff(data, geoTrans, spatialRef, 'FLOAT', 0, outFile)
  # If you opened it, you close it:
  if opened_file:
    dataset.close()
  return geotiff_paths


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='time_series2geotiff',
    description='extracts time series layers and stores them in GeoTIFF format',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('inFile', metavar='<input file>', action="store", type=file_exists, 
    help='name of the netCDF time series file')
  parser.add_argument('outDir', metavar='<output directory>', action="store", type=dir_exists_create, 
    help='name of the output directory')
  parser.add_argument('--listFile', metavar='<granule list>', action="store", type=file_exists,
    help='name of the granule list file')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  ### Read granule list
  if args.listFile != None:
    listFile = [line.rstrip() for line in open(args.listFile)]

  time_series2geotiff(args.inFile, args.outDir, granuleList=listFile)

