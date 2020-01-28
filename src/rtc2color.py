#!/usr/bin/python

import argparse
from argparse import RawTextHelpFormatter
import sys
import numpy as np
from osgeo import gdal, osr


def rtc2color(fullpolFile, crosspolFile, threshold, geotiff, cleanup=False,
  teal=False, amp=False, real=False):

  # Suppress GDAL warnings
  gdal.UseExceptions()
  gdal.PushErrorHandler('CPLQuietErrorHandler')

  # Convert threshold to power scale
  g = pow(10.0, np.float32(threshold)/10.0)

  # Read input parameter
  fullpol = gdal.Open(fullpolFile)
  crosspol = gdal.Open(crosspolFile)
  cpCols = fullpol.RasterXSize
  cpRows = fullpol.RasterYSize
  xpCols = crosspol.RasterXSize
  xpRows = crosspol.RasterYSize
  cols = min(cpCols, xpCols)
  rows = min(cpRows, xpRows)
  geotransform = fullpol.GetGeoTransform()
  originX = geotransform[0]
  originY = geotransform[3]
  pixelWidth = geotransform[1]
  pixelHeight = geotransform[5]

  # Estimate memory required...
  size = float((rows*cols)/(1024*1024*1024))

  # print('float16 variables: cp,xp,diff,zp,rp,bp,red = {} GB'.format(size*14))
  # print('uint8 variables: mask, blue_mask = {} GB".format(size*2))

  print('Data size is {} lines by {} samples ({} Gpixels)'.format(rows,cols,size))
  print('Estimated Total RAM usage = {} GB'.format(size*16))

  # Read full-pol image
  print('Reading full-pol image (%s)' % fullpolFile)
  data = fullpol.GetRasterBand(1).ReadAsArray()
  cp = (data[:rows, :cols]).astype(np.float16)
  data = None
  cp[np.isnan(cp)] = 0
  cp[cp < 0] = 0
  if cleanup == True:
    cp[cp < 0.0039811] = 0
  if amp == True:
    cp = cp*cp

  # Read cross-pol image
  print('Reading cross-pol image (%s)' % crosspolFile)
  data = crosspol.GetRasterBand(1).ReadAsArray()
  xp = (data[:rows, :cols]).astype(np.float16)
  data = None
  xp[np.isnan(xp)] = 0
  xp[xp < 0] = 0
  if cleanup == True:
    xp[xp < 0.0039811] = 0
  if amp == True:
    xp = xp*xp

  # Calculate color decomposition
  print('Calculating color decomposition components')

  mask = (cp > xp).astype(np.uint8)
  diff = (cp - xp).astype(np.float16)
  diff[diff < 0] = 0
  zp = (np.arctan(np.sqrt(diff))*2.0/np.pi*mask).astype(np.float16)
  mask = (cp > 3.0*xp).astype(np.uint8)
  diff = cp - 3.0*xp
  diff[diff < 0] = 0
  rp = (np.sqrt(diff)*mask).astype(np.float16)

  mask = (3.0*xp > cp).astype(np.uint8)
  if teal == False:
    mask = 0
  diff = 3.0*xp - cp
  diff[diff < 0] = 0
  bp = (np.sqrt(diff)*mask).astype(np.float16)
  mask = (xp > 0).astype(np.uint8)
  blue_mask = (xp < g).astype(np.uint8)

  # Write output GeoTIFF
  driver = gdal.GetDriverByName('GTiff')
  if real == True:
    outRaster = driver.Create(geotiff, cols, rows, 3, gdal.GDT_Float32,
      ['COMPRESS=LZW'])
  else:
    outRaster = driver.Create(geotiff, cols, rows, 3, gdal.GDT_Byte,
      ['COMPRESS=LZW'])
  outRaster.SetGeoTransform((originX, pixelWidth, 0, originY, 0, pixelHeight))
  outRasterSRS = osr.SpatialReference()
  outRasterSRS.ImportFromWkt(fullpol.GetProjectionRef())
  outRaster.SetProjection(outRasterSRS.ExportToWkt())
  fullpol = None
  crosspol = None

  print('Calculate red channel and save in GeoTIFF')
  outBand = outRaster.GetRasterBand(1)
  if real == True:
    red = (2.0*rp*(1 - blue_mask) + zp*blue_mask)
  else:
    red = (2.0*rp*(1 - blue_mask) + zp*blue_mask)*255
  red[red==0] = 1
  red = red * mask

  outBand.WriteArray(red)
  red = None
  print('Calculate green channel and save in GeoTIFF')
  outBand = outRaster.GetRasterBand(2)
  if real == True:
    green = (3.0*np.sqrt(xp)*(1 - blue_mask) + 2.0*zp*blue_mask)
  else:
    green = (3.0*np.sqrt(xp)*(1 - blue_mask) + 2.0*zp*blue_mask)*255
  green[green==0]=1
  green = green * mask
  outBand.WriteArray(green)
  green = None
  print('Calculate blue channel and save in GeoTIFF')
  outBand = outRaster.GetRasterBand(3)
  if real == True:
    blue = (2.0*bp*(1 - blue_mask) + 5.0*zp*blue_mask)
  else:
    blue = (2.0*bp*(1 - blue_mask) + 5.0*zp*blue_mask)*255
  blue[blue==0] = 1
  blue = blue * mask
  outBand.WriteArray(blue)
  blue = None
  xp = None
  cp = None
  zp = None
  bp = None
  blue_mask = None
  outRaster = None


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='rtc2color',
    description='Converts a dual-pol RTC to a color GeoTIFF',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('fullpol', help='name of the full-pol RTC file (input)')
  parser.add_argument('crosspol', help='name of the cross-pol RTC (input)')
  parser.add_argument('threshold', help='threshold value in dB (input)')
  parser.add_argument('geotiff', help='name of color GeoTIFF file (output)')
  parser.add_argument('-cleanup', action='store_true', help='clean up artifacts in powerscale images')
  parser.add_argument('-teal', action='store_true', help='extend the blue band with teal')
  parser.add_argument('-amp', action='store_true', help='input is amplitude, not powerscale')
  parser.add_argument('-float', action='store_true', help='save as floating point')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  rtc2color(args.fullpol, args.crosspol, args.threshold, args.geotiff,
    args.cleanup, args.teal, args.amp, args.float)
