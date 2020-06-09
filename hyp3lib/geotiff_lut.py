"""Applies a LUT to a GeoTIFF"""

import argparse
import os

import numpy as np
from osgeo import gdal, osr


def geotiff_lut(geotiff, lutFile, outFile):

  # Suppress GDAL warnings
  gdal.UseExceptions()
  gdal.PushErrorHandler('CPLQuietErrorHandler')

  # Read GeoTIFF and normalize it (if needed)
  inRaster = gdal.Open(geotiff)
  cols = inRaster.RasterXSize
  rows = inRaster.RasterYSize
  geotransform = inRaster.GetGeoTransform()
  originX = geotransform[0]
  originY = geotransform[3]
  pixelWidth = geotransform[1]
  pixelHeight = geotransform[5]
  data = inRaster.GetRasterBand(1).ReadAsArray()
  dataType = gdal.GetDataTypeName(inRaster.GetRasterBand(1).DataType)
  if dataType == 'Byte':
    index = data
  else:
    data[np.isnan(data)] = 0.0
    data = data.astype(np.float32)
    mean = np.mean(data)
    std_dev = np.std(data)
    minValue = max(np.min(data), mean-2.0*std_dev)
    maxValue = min(np.max(data), mean+2.0*std_dev)
    data -= minValue
    data /= maxValue
    data[data>1.0] = 1.0
    data = data*255.0 + 0.5
    index = data.astype(np.uint8)
  data = None

  # Read look up table
  lut = np.genfromtxt(lutFile, delimiter = ',', dtype = int)
  redLut = lut[:, 0]
  greenLut = lut[:, 1]
  blueLut = lut[:, 2]

  # Apply look up table
  red = np.zeros((rows, cols), dtype = np.uint8)
  green = np.zeros((rows, cols), dtype = np.uint8)
  blue = np.zeros((rows, cols), dtype = np.uint8)
  red = redLut[index]
  green = greenLut[index]
  blue = blueLut[index]

  # Write RGB GeoTIFF image
  driver = gdal.GetDriverByName('GTiff')
  outRaster = driver.Create(outFile, cols, rows, 3, gdal.GDT_Byte,
    ['COMPRESS=LZW'])
  outRaster.SetGeoTransform((originX, pixelWidth, 0, originY, 0, pixelHeight))
  outRasterSRS = osr.SpatialReference()
  outRasterSRS.ImportFromWkt(inRaster.GetProjectionRef())
  outRaster.SetProjection(outRasterSRS.ExportToWkt())
  outBand = outRaster.GetRasterBand(1)
  outBand.WriteArray(red)
  outBand = outRaster.GetRasterBand(2)
  outBand.WriteArray(green)
  outBand = outRaster.GetRasterBand(3)
  outBand.WriteArray(blue)
  outRaster = None


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('geotiff', help='name of GeoTIFF file (input)')
    parser.add_argument('lut', help='name of look up table file to apply (input)')
    parser.add_argument('output', help='name of output file (output)')
    args = parser.parse_args()

    if not os.path.exists(args.geotiff):
        parser.error(f'GeoTIFF file {args.geotiff} does not exist!')

    geotiff_lut(args.geotiff, args.lut, args.output)


if __name__ == '__main__':
    main()
