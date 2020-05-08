"""Generates pre-event and post-event RTCs to a color difference GeoTIFF"""

from __future__ import print_function, absolute_import, division, unicode_literals

import os
import argparse
import datetime
from osgeo import gdal, osr
from hyp3lib.asf_geometry import geotiff2polygon, overlap_indices, geotiff_overlap
from hyp3lib.rtc2color import rtc2color
from hyp3lib.execute import execute


class FileException(Exception):
  """File does not exist"""


def check_pixelsize(preFullpol, postFullpol):

  pre = gdal.Open(preFullpol)
  gt = pre.GetGeoTransform()
  prePixelsize = gt[1]
  pre = None
  post = gdal.Open(postFullpol)
  gt = post.GetGeoTransform()
  postPixelsize = gt[1]
  if prePixelsize != postPixelsize:
    error = ('Pixel sizes in pre-event (%f) and post-event (%f) images differ.' % \
      (prePixelsize, postPixelsize))
    raise ValueError(error)


# This function assumes that we are looking at UTM projected images
def check_projection(tmpDir, preFullpol, preCrosspol, postFullpol, postCrosspol):

  pre = gdal.Open(preFullpol)
  gt = pre.GetGeoTransform()
  pixelSize = gt[1]
  preSpatialRef = osr.SpatialReference()
  preSpatialRef.ImportFromWkt(pre.GetProjectionRef())
  post = gdal.Open(postFullpol)
  postSpatialRef = osr.SpatialReference()
  postSpatialRef.ImportFromWkt(post.GetProjectionRef())
  geoSpatialRef = osr.SpatialReference()
  geoSpatialRef.ImportFromEPSG(4326)
  preCoordTrans = osr.CoordinateTransformation(preSpatialRef, geoSpatialRef)
  postCoordTrans = osr.CoordinateTransformation(postSpatialRef, geoSpatialRef)
  prePoly = geotiff2polygon(preFullpol)
  prePoly.Transform(preCoordTrans)
  preCentroid = prePoly.Centroid()
  preUtm = int((preCentroid.GetX() + 180.0)/6.0 + 1.0)
  postPoly = geotiff2polygon(postFullpol)
  postPoly.Transform(postCoordTrans)
  postCentroid = postPoly.Centroid()
  postUtm = int((postCentroid.GetX() + 180.0)/6.0 + 1.0)
  overlap = prePoly.Intersection(postPoly)
  overlapCentroid = overlap.Centroid()
  overlapUtm = int((overlapCentroid.GetX() + 180.0)/6.0 + 1.0)

  if preUtm != postUtm:
    print('Pre- and post-event images in different UTM zones.')
    if preUtm == overlapUtm:
      print('Reprojecting post-event images to UTM zone %d' % overlapUtm)
      if postCentroid.GetY() > 0.0:
        proj = ('EPSG:326{0}'.format(preUtm))
      else:
        proj = ('EPSG:327{0}'.format(preUtm))
      fullpol = os.path.join(tmpDir, 'postFullpol.tif')
      cmd = ("gdalwarp -r bilinear -tr %f %f -t_srs %s %s %s" % \
        (pixelSize, pixelSize, proj, postFullpol, fullpol))
      execute(cmd)
      postFullpol = fullpol
      crosspol = os.path.join(tmpDir, 'postCrosspol.tif')
      cmd = ("gdalwarp -r bilinear -tr %f %f -t_srs %s %s %s" % \
        (pixelSize, pixelSize, proj, postCrosspol, crosspol))
      execute(cmd)
      postCrosspol = crosspol
    if postUtm == overlapUtm:
      print('Reprojecting post-event images to UTM zone %d' % overlapUtm)
      if postCentroid.GetY() > 0.0:
        proj = ('EPSG:326{0}'.format(postUtm))
      else:
        proj = ('EPSG:327{0}'.format(postUtm))
      fullpol = os.path.join(tmpDir, 'preFullpol.tif')
      execute("gdalwarp -r bilinear -tr %f %f -t_srs %s %s %s" % \
        (pixelSize, pixelSize, proj, preFullpol, fullpol))
      preFullpol = fullpol
      crosspol = os.path.join(tmpDir, 'preCrosspol.tif')
      execute("gdalwarp -r bilinear -tr %f %f -t_srs %s %s %s" % \
        (pixelSize, pixelSize, proj, preCrosspol, crosspol))
      preCrosspol = crosspol

  return (preFullpol, preCrosspol, postFullpol, postCrosspol)


def make_tmp_dir(path, prefix):
    # Generate the temporary directory in location defined in the configuration
    # file states. As general failover method generate a temporary directory in
    # the current directory

    tmpStr = prefix + '_' + datetime.datetime.utcnow().isoformat()
    if path:
        tmpDir = os.path.join(path, tmpStr)
    else:
        tmpDir = tmpStr
    os.makedirs(tmpDir)

    return tmpDir


def rtc2colordiff(preFullpol, preCrosspol, postFullpol, postCrosspol, threshold,
  geotiff, teal, amp):

  print('Converting RTC dual-pol data to color GeoTIFF')

  # Check whether the input files actually exist
  if not os.path.exists(preFullpol):
    error = ('Pre-event RTC full-pol file (%s) does not exist!' % preFullpol)
    raise FileException(error)

  if not os.path.exists(preCrosspol):
    error = ('Pre-event RTC cross-pol file (%s) does not exist!' % preCrosspol)
    raise FileException(error)

  if not os.path.exists(postFullpol):
    error = ('Post-event RTC full-pol file (%s) does not exist!' % postFullpol)
    raise FileException(error)

  if not os.path.exists(postCrosspol):
    error = ('Post-event RTC cross-pol file (%s) does not exist!' %
      postCrosspol)
    raise FileException(error)

  # Generating a temporary directory
  dirName = os.path.dirname(os.path.abspath(geotiff))
  tmpDir = make_tmp_dir(dirName, 'color')

  # Check pixel sizes of pre- and post-event image
  check_pixelsize(preFullpol, postFullpol)

  # Reproject files if necessary
  (preFullpol, preCrosspol, postFullpol, postCrosspol) = \
    check_projection(tmpDir, preFullpol, preCrosspol, postFullpol, postCrosspol)

  # Determine common overlap of pre- and post-event files
  (prePolygon, postPolygon, overlap, proj, pixelSize) = \
    geotiff_overlap(preFullpol, postFullpol, 'intersection')
  (xPreOff, yPreOff, xPreCount, yPreCount) = \
    overlap_indices(prePolygon, overlap, pixelSize)
  (xPostOff, yPostOff, xPostCount, yPostCount) = \
    overlap_indices(postPolygon, overlap, pixelSize)

  # Calculating pre- and post-event RGB images
  colorPreFile = os.path.join(tmpDir, 'preColor.tif')
  rtc2color(preFullpol, preCrosspol, threshold, colorPreFile, amp=amp, real=True)
  colorPostFile = os.path.join(tmpDir, 'postColor.tif')
  rtc2color(postFullpol, postCrosspol, threshold, colorPostFile, amp=amp, real=True)

  # Read input parameter
  colorPreImg = gdal.Open(colorPreFile)
  colorPostImg = gdal.Open(colorPostFile)
  cols = xPreCount
  rows = yPreCount
  geotransform = colorPreImg.GetGeoTransform()
  originX = geotransform[0]
  originY = geotransform[3]
  pixelWidth = geotransform[1]
  pixelHeight = geotransform[5]

  # Read color images
  print('Reading pre-color image (%s)' % os.path.basename(colorPreFile))
  preGreen = colorPreImg.GetRasterBand(2).ReadAsArray()
  print('Reading post-color image (%s)' % os.path.basename(colorPostFile))
  postRed = colorPostImg.GetRasterBand(1).ReadAsArray()
  postGreen = colorPostImg.GetRasterBand(2).ReadAsArray()

  # Calculate color difference image
  print('Calculating color difference')
  xPreEnd = xPreOff + xPreCount
  yPreEnd = yPreOff + yPreCount
  xPostEnd = xPostOff + xPostCount
  yPostEnd = yPostOff + yPostCount
  preGreen = preGreen[yPreOff:yPreEnd, xPreOff:xPreEnd]
  postRed = postRed[yPostOff:yPostEnd, xPostOff:xPostEnd]
  postGreen = postGreen[yPostOff:yPostEnd, xPostOff:xPostEnd]
  preMask = (preGreen > 0).astype(int)
  postMask = (postGreen > 0).astype(int)
  mask = preMask*postMask
  red = postRed*255*mask
  green = postGreen*255*mask
  blue = 5.0*(postGreen - preGreen)*255*mask

  # Write output GeoTIFF
  print('Writing color difference image to GeoTIFF (%s)' % geotiff)
  driver = gdal.GetDriverByName('GTiff')
  outRaster = driver.Create(geotiff, cols, rows, 3, gdal.GDT_Byte,
    ['COMPRESS=LZW'])
  outRaster.SetGeoTransform((originX, pixelWidth, 0, originY, 0, pixelHeight))
  outRasterSRS = osr.SpatialReference()
  outRasterSRS.ImportFromWkt(colorPreImg.GetProjectionRef())
  outRaster.SetProjection(outRasterSRS.ExportToWkt())
  outBand = outRaster.GetRasterBand(1)
  outBand.WriteArray(red)
  outBand = outRaster.GetRasterBand(2)
  outBand.WriteArray(green)
  outBand = outRaster.GetRasterBand(3)
  outBand.WriteArray(blue)
  outRaster = None

  # Cleanup intermediate files
  os.remove(os.path.join(tmpDir, colorPreFile))
  os.remove(os.path.join(tmpDir, colorPostFile))
  os.rmdir(tmpDir)


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('preFullpol', help='name of the pre-event full-pol RTC file (input)')
    parser.add_argument('preCrosspol', help='name of the pre-event cross-pol RTC (input)')
    parser.add_argument('postFullpol', help='name of the post-event full-pol RTC file (input)')
    parser.add_argument('postCrosspol', help='name of the post-event cross-pol RTC file (input)')
    parser.add_argument('threshold', help='threshold value in dB (input)')
    parser.add_argument('geotiff', help='name of color difference GeoTIFF file (output)')
    parser.add_argument('-teal', action='store_true', help='extend the blue band with teal')
    parser.add_argument('-amp', action='store_true', help='input is amplitude, not powerscale')
    args = parser.parse_args()

    rtc2colordiff(args.preFullpol, args.preCrosspol, args.postFullpol,
                  args.postCrosspol, args.threshold, args.geotiff, args.teal, args.amp)


if __name__ == '__main__':
    main()
