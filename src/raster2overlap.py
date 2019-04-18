#!/usr/bin/python

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from osgeo import gdal, ogr, osr
from asf_geometry import *

tolerance = 0.05


def raster2overlap(inFile1, inFile2):

  ## Generate output names
  outFile1 = inFile1.replace('.tif', '_overlap.tif')
  outFile2 = inFile2.replace('.tif', '_overlap.tif')

  ## Calculate boundary masks
  print('Creating boundary mask ({0}) ...'.format(os.path.basename(inFile1)))
  (mask1, colFirst1, rowFirst1, gt1, proj1) = geotiff2boundary_mask(inFile1)
  print('Creating boundary mask ({0}) ...'.format(os.path.basename(inFile2)))
  (mask2, colFirst2, rowFirst2, gt2, proj2) = geotiff2boundary_mask(inFile2)
  if proj1.GetAttrValue('AUTHORITY', 0) == 'EPSG':
    epsg1 = int(proj1.GetAttrValue('AUTHORITY', 1))
  if proj2.GetAttrValue('AUTHORITY', 0) == 'EPSG':
    epsg2 = int(proj2.GetAttrValue('AUTHORITY', 1))
  if epsg1 != epsg2:
    print('Projection of the two GeoTIFFs differ! Not handled yet.')
    sys.exit(1)
  if np.abs(gt1[1] - gt2[1]) > tolerance:
    print('Pixel widths differ ({0} versus {1})'.format(gt1[1], gt2[1]))
    sys.exit(1)
  if np.abs(gt1[5] - gt2[5]) > tolerance:
    print('Pixel heights differ ({0} versus {1})'.format(np.abs(gt1[5]),
      np.abs(gt2[5])))
    sys.exit(1)

  ## Determine overlap of the two masks
  #print('Determining overlap ...')
  (mask, gt) = raster_overlap(mask1, gt1, mask2, gt2)

  ## Cut blackfill around mask
  #print('Cutting blackfill ...')
  (mask, colFirst, rowFirst, gt) = cut_blackfill(mask, gt)

  maskFile = ('mask_overlap.tif')
  data2geotiff(mask, gt, proj1, 'BYTE', 0, maskFile)

  ## Apply mask to image
  outFile1 = inFile1.replace('.tif','_overlap.tif')
  print('Applying mask to image ({0}) ...'.format(os.path.basename(outFile1)))
  inRaster = gdal.Open(inFile1)
  dataGeoTrans = inRaster.GetGeoTransform()
  data = inRaster.GetRasterBand(1).ReadAsArray()
  data = apply_mask(data, dataGeoTrans, mask, gt)
  data2geotiff(data, gt, proj1, 'FLOAT', np.nan, outFile1)

  outFile2 = inFile2.replace('.tif','_overlap.tif')
  print('Applying mask to image ({0}) ...'.format(os.path.basename(outFile2)))
  inRaster = gdal.Open(inFile2)
  dataGeoTrans = inRaster.GetGeoTransform()
  data = inRaster.GetRasterBand(1).ReadAsArray()
  data = apply_mask(data, dataGeoTrans, mask, gt)
  data2geotiff(data, gt, proj1, 'FLOAT', np.nan, outFile2)


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='raster2overlap',
    description='cuts down two GeoTIFF files to the common overlap',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('input1', metavar='<geotiff file 1>',
    help='name of the first GeoTIFF file')
  parser.add_argument('input2', metavar='<geotiff file 2>',
    help='name of the second GeoTIFF file')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.input1):
    print('GeoTIFF file (%s) does not exist!' % args.input1)
    sys.exit(1)
  if not os.path.exists(args.input2):
    print('GeoTIFF file (%s) does not exist!' % args.input2)
    sys.exit(1)

  raster2overlap(args.input1, args.input2)
