#!/usr/bin/python

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from datetime import datetime
from osgeo import gdal, ogr, osr
from osgeo.gdalconst import *
import shutil
from asf_time_series import *


def rasterStatsImage(inFile, measure, size, outFile):

  ### Extract metadata
  (proj, gt, shape, pixel) = raster_meta(inFile)
  originX = gt[0]
  originY = gt[3]
  pixelWidth = gt[1]*size
  pixelHeight = gt[5]*size
  (rows, cols) = shape

  ### Read original image
  inRaster = gdal.Open(inFile)
  image = inRaster.GetRasterBand(1).ReadAsArray()
  inRaster = None

  ### Slice the image and extract stats while doing so
  cols = int(np.rint(cols/size)*size)
  rows = int(np.rint(rows/size)*size)
  subCols = cols/size
  subRows = rows/size
  value = np.full((subRows, subCols), np.nan)
  for ii in xrange(0,rows-size,size):
    for kk in xrange(0,cols-size,size):
      row = kk/size
      col = ii/size
      subImage = image[ii:ii+size, kk:kk+size]
      if measure == 'mean':
        value[col, row] = np.mean(subImage)
      elif measure == 'min':
        value[col, row] = np.min(subImage)
      elif measure == 'max':
        value[col, row] = np.max(subImage)
      elif measure == 'std':
        value[col, row] = np.std(subImage)

  ### Save the stats in separate GeoTIFF images (for the moment)
  driver = gdal.GetDriverByName('GTiff')
  outRaster = driver.Create(outFile, subCols, subRows, 1, gdal.GDT_Float32,
    ['COMPRESS=DEFLATE'])
  outRaster.SetGeoTransform((originX, pixelWidth, 0, originY, 0, pixelHeight))
  outRaster.SetProjection(proj.ExportToWkt())
  outRaster.SetMetadataItem('AREA_OR_POINT', pixel)
  outBand = outRaster.GetRasterBand(1)
  outBand.WriteArray(value)
  outRaster = None

  return value


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='rasterStatsImage',
    description='calculates a statistical measure for a subsampled GeoTIFF ' \
    'image', formatter_class=RawTextHelpFormatter)
  parser.add_argument('input', metavar='<input file>',
    help='name of the input GeoTIFF file')
  parser.add_argument('measure', metavar='<measure>',
    help='measure to calculate: mean, min, max, std')
  parser.add_argument('size', metavar='<size>',
    help='window size for calculation')
  parser.add_argument('output', metavar='<output file>',
    help='name of the output GeoTiff file')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.input):
    print('GeoTIFF list file (%s) does not exist!' % args.input)
    sys.exit(1)

  rasterStatsImage(args.input, args.measure, int(args.size), args.output)
