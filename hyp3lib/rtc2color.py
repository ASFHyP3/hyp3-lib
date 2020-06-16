"""RGB decomposition of a dual-pol RTC

The RGB decomposition enhances RTC dual-pol data for visual interpretation. It
decomposes the co-pol and cross-pol signal into these color channels:
    red: simple bounce (polarized) with some volume scattering
    green: volume (depolarized) scattering
    blue: simple bounce with very low volume scattering

In the case where the volume to simple scattering ratio is larger than expected
for typical vegetation, such as in glaciated areas or some forest types, a teal
color (green + blue) is used.
"""

import argparse
import os
from pathlib import Path
from typing import Union

import numpy as np
from osgeo import gdal, osr


def rtc2color(copol_tif: Union[str, Path], crosspol_tif: Union[str, Path], threshold: float, out_tif: Union[str, Path],
              cleanup=False, teal=False, amp=False, real=False):
  """RGB decomposition of a dual-pol RTC

  Args:
      copol_tif: Path to the co-pol GeoTIF
      crosspol_tif: Path to the cross-pol GeoTIF
      threshold: Decomposition threshold in db
      out_tif: Path to the output GeoTIF
      cleanup: Cleanup bad data using a -24 db threshold for valid pixels
      teal: Combine green and blue channels because the volume to simple scattering ratio is high
      amp: input TIFs are in amplitude and not power
      real: Output floating point values instead of RGB scaled (0--255) ints
  """
  # FIXME: Can we just determine if we should use teal?

  # Suppress GDAL warnings
  gdal.UseExceptions()
  gdal.PushErrorHandler('CPLQuietErrorHandler')

  # Convert threshold to power scale
  g = pow(10.0, np.float32(threshold)/10.0)

  # Read input parameter
  fullpol = gdal.Open(copol_tif)
  crosspol = gdal.Open(crosspol_tif)
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
  size = float(rows*cols)/float(1024*1024*1024)

  # print('float16 variables: cp,xp,diff,zp,rp,bp,red = {} GB'.format(size*14))
  # print('uint8 variables: mask, blue_mask = {} GB".format(size*2))

  print('Data size is {} lines by {} samples ({} Gpixels)'.format(rows,cols,size))
  print('Estimated Total RAM usage = {} GB'.format(size*16))

  # Read full-pol image
  print('Reading full-pol image (%s)' % out_tif)
  data = fullpol.GetRasterBand(1).ReadAsArray()
  cp = (data[:rows, :cols]).astype(np.float16)
  data = None
  cp[np.isnan(cp)] = 0
  # FIXME: do we get negative powers from RTC?
  cp[cp < 0] = 0
  if cleanup == True:
    cp[cp < 0.0039811] = 0
  # FIXME: Should this be applied *before* the above cleanup?
  if amp == True:
    cp = cp*cp

  # Read cross-pol image
  print('Reading cross-pol image (%s)' % crosspol_tif)
  data = crosspol.GetRasterBand(1).ReadAsArray()
  xp = (data[:rows, :cols]).astype(np.float16)
  data = None
  xp[np.isnan(xp)] = 0
  xp[xp < 0] = 0
  if cleanup == True:
      # FIXME: Is this the correct value? 0.0039811 ~= pow(10.0, -24.0 / 10.0),
      #        or our default threshold
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
    outRaster = driver.Create(out_tif, cols, rows, 3, gdal.GDT_Float32,
      ['COMPRESS=LZW'])
  else:
    outRaster = driver.Create(out_tif, cols, rows, 3, gdal.GDT_Byte,
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
    # FIXME: Should we *scale* this? There are values over 1
    red = (2.0*rp*(1 - blue_mask) + zp*blue_mask)*255
  # FIXME: We should be *adding* 1 I think... values less than 1 will be between
  #        the no data value and our minimum valid value...
  red[red==0] = 1
  # FIXME: Is this the right mask (xp > 0)? Red should be mostly copol
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
  # FIXME: Is this the right mask (xp > 0)? Green should be both copol and crosspol
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
  # FIXME: Is this the right mask (xp > 0)? Blue should be only copol and no crosspol
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

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('copol', help='name of the co-pol RTC file (input)')
    parser.add_argument('crosspol', help='name of the cross-pol RTC (input)')
    parser.add_argument('threshold', type=float, help='threshold value in dB (input)')
    parser.add_argument('geotiff', help='name of color GeoTIFF file (output)')
    parser.add_argument('-cleanup', action='store_true', help='clean up artifacts in powerscale images')
    parser.add_argument('-teal', action='store_true', help='extend the blue band with teal')
    parser.add_argument('-amp', action='store_true', help='input is amplitude, not powerscale')
    parser.add_argument('-float', action='store_true', help='save as floating point')
    args = parser.parse_args()

    rtc2color(args.copol, args.crosspol, args.threshold, args.geotiff,
              args.cleanup, args.teal, args.amp, args.float)


if __name__ == '__main__':
    main()
