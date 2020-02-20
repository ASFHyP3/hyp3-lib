#!/usr/bin/env python
"""Converts a dual-pol RTC to a color GeoTIFF"""

from __future__ import print_function, absolute_import, division, unicode_literals

import argparse
import os
import sys
import numpy as np
from osgeo import gdal, osr


def rtc2color(fullpolFile, crosspolFile, threshold, geotiff, cleanup=False,
  teal=False, amp=False, float=False):

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

  # Read full-pol image
  print('Reading full-pol image (%s)' % fullpolFile)
  data = fullpol.GetRasterBand(1).ReadAsArray()
  cp = data[:rows, :cols]
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
  xp = data[:rows, :cols]
  data = None
  xp[np.isnan(xp)] = 0
  xp[xp < 0] = 0
  if cleanup == True:
    xp[xp < 0.0039811] = 0
  if amp == True:
    xp = xp*xp

  # Calculate color decomposition
  print('Calculating color decomposition components')
  mask = (cp > xp).astype(int)
  diff = cp - xp
  diff[diff < 0] = 0
  zp = np.arctan(np.sqrt(diff))*2.0/np.pi*mask

  mask = (cp > 3.0*xp).astype(int)
  diff = cp - 3.0*xp
  diff[diff < 0] = 0
  rp = np.sqrt(diff)*mask

  mask = (3.0*xp > cp).astype(int)
  if teal == False:
    mask = 0
  diff = 3.0*xp - cp
  diff[diff < 0] = 0
  bp = np.sqrt(diff)*mask

  mask = (xp > 0).astype(int)

  blue_mask = (xp < g).astype(int)

  # Write output GeoTIFF
  driver = gdal.GetDriverByName('GTiff')
  if float == True:
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
  if float == True:
    red = (2.0*rp*(1 - blue_mask) + zp*blue_mask)
  else:
    red = (2.0*rp*(1 - blue_mask) + zp*blue_mask)*255
  red[red==0] = 1
  red = red * mask
  outBand.WriteArray(red)
  red = None
  print('Calculate green channel and save in GeoTIFF')
  outBand = outRaster.GetRasterBand(2)
  if float == True:
    green = (3.0*np.sqrt(xp)*(1 - blue_mask) + 2.0*zp*blue_mask)
  else:
    green = (3.0*np.sqrt(xp)*(1 - blue_mask) + 2.0*zp*blue_mask)*255
  green[green==0]=1
  green = green * mask
  outBand.WriteArray(green)
  green = None
  print('Calculate blue channel and save in GeoTIFF')
  outBand = outRaster.GetRasterBand(3)
  if float == True:
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


def main():
    """Main entrypoint"""

    # entrypoint name can differ from module name, so don't pass 0-arg
    cli_args = sys.argv[1:] if len(sys.argv) > 1 else None

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('fullpol', help='name of the full-pol RTC file (input)')
    parser.add_argument('crosspol', help='name of the cross-pol RTC (input)')
    parser.add_argument('threshold', help='threshold value in dB (input)')
    parser.add_argument('geotiff', help='name of color GeoTIFF file (output)')
    parser.add_argument('-cleanup', action='store_true', help='clean up artifacts in powerscale images')
    parser.add_argument('-teal', action='store_true', help='extend the blue band with teal')
    parser.add_argument('-amp', action='store_true', help='input is amplitude, not powerscale')
    parser.add_argument('-float', action='store_true', help='save as floating point')
    args = parser.parse_args(cli_args)

    rtc2color(args.fullpol, args.crosspol, args.threshold, args.geotiff,
              args.cleanup, args.teal, args.amp, args.float)


if __name__ == '__main__':
    main()
