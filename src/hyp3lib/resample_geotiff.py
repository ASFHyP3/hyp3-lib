"""Resamples a GeoTIFF file and saves it in a number of formats"""

import argparse
import glob
import math
import os
import zipfile

import lxml.etree as et
from osgeo import gdal
from osgeo.gdalconst import GRIORA_Cubic, GRIORA_NearestNeighbour


def resample_geotiff(geotiff, width, outFormat, outFile, use_nn = False):

  # Check output format
  formats = ['GEOTIFF', 'JPEG', 'JPG', 'PNG', 'KML']
  if outFormat.upper() not in formats:
    raise ValueError(f'Unknown output format ({outFormat.upper()})! Accepted formats: {formats}')
  if use_nn:
      resampleMethod = GRIORA_NearestNeighbour
  else:
      resampleMethod = GRIORA_Cubic

  # Suppress GDAL warnings
  gdal.UseExceptions()
  gdal.PushErrorHandler('CPLQuietErrorHandler')

  # Extract information from GeoTIFF
  raster = gdal.Open(geotiff)
  bandCount = raster.RasterCount
  band = raster.GetRasterBand(1)
  colorTable = band.GetColorTable()

  # Downsample by multiples of pixel size to avoid interpolation issues
  # (if needed)
  orgExt = os.path.splitext(outFile)[1]
  resampleFile = None
  resampleFile2 = None
  gt = raster.GetGeoTransform()
  cols = raster.RasterXSize
  # rows = raster.RasterYSize
  scale = cols / float(width)
  mult = 2 ** (math.floor(math.log(scale,2))-1)
  
  if mult > 1:
    pixelWidth = gt[1] * mult
    pixelHeight = gt[5] * mult
    if outFormat.upper() == 'PNG' and bandCount == 3: 
      tmpExt = ('_resamp{0}.png'.format(os.getpid()))
      resampleFile = outFile.replace(orgExt, tmpExt)
      tmpExt2 = ('_resamp2{0}.png'.format(os.getpid()))
      resampleFile2 = outFile.replace(orgExt, tmpExt2)
      gdal.Translate(resampleFile,raster,format='PNG',noData='0 0 0')
      gdal.Translate(resampleFile2,resampleFile, resampleAlg=resampleMethod, format='PNG',
        xRes=pixelWidth, yRes=pixelHeight, noData="0 0 0")
      raster = gdal.Open(resampleFile2)
    else:
      tmpExt = ('_resamp{0}.tif'.format(os.getpid()))
      resampleFile = outFile.replace(orgExt, tmpExt)
      gdal.Translate(resampleFile, raster, resampleAlg=resampleMethod,
          xRes=pixelWidth, yRes=pixelHeight, noData="0")
      raster = gdal.Open(resampleFile)

  # Resample image using cubic interpolation
  # Save it in the various image formats
  if outFormat.upper() == 'GEOTIFF':
    gdal.Translate(outFile, raster, resampleAlg=resampleMethod, width=width)
  elif outFormat.upper() == 'JPEG' or outFormat.upper() == 'JPG':
    if colorTable is None:
      gdal.Translate(outFile, raster, format='JPEG', resampleAlg=resampleMethod,
        width=width)
    else:
      gdal.Translate(outFile, raster, format='JPEG', resampleAlg=resampleMethod,
        width=width, rgbExpand='RGB')
  elif outFormat.upper() == 'PNG':
    if bandCount == 1:
      gdal.Translate(outFile, raster, format='PNG', resampleAlg=resampleMethod,
        width=width, noData='0')
    elif bandCount == 3:
      gdal.Translate(outFile, raster, format='PNG', resampleAlg=resampleMethod,
        width=width, noData='0 0 0')
  elif outFormat.upper() == 'KML':

    # Reproject to geographic coordinates first
    tmpExt = ('_geo{0}.tif'.format(os.getpid()))
    tmpFile = outFile.replace(orgExt, tmpExt)
    rgbFile = None
    if bandCount == 1:
      if colorTable is None:
        gdal.Warp(tmpFile, raster, resampleAlg=GRIORA_Cubic, width=width,
          srcNodata='0', dstSRS='EPSG:4326', dstAlpha=True)
      else:
        rgbExt = ('_rgb{0}.tif'.format(os.getpid()))
        rgbFile = outFile.replace(orgExt, rgbExt)
        gdal.Translate(rgbFile, raster, rgbExpand='RGBA')
        raster = gdal.Open(rgbFile)
        gdal.Warp(tmpFile, raster, resampleAlg=GRIORA_Cubic, width=width,
          srcNodata='0', dstSRS='EPSG:4326', dstAlpha=True)
    elif bandCount == 3:
      gdal.Warp(tmpFile, raster, resampleAlg=GRIORA_Cubic, width=width,
        srcNodata='0 0 0', dstSRS='EPSG:4326', dstAlpha=True)
    raster = None

    # Convert GeoTIFF to PNG - since warp cannot do that in one step
    raster = gdal.Open(tmpFile)
    pngFile = outFile.replace(orgExt, '.png')
    gdal.Translate(pngFile, raster, format='PNG', resampleAlg=resampleMethod)

    # Extract metadata from GeoTIFF to fill into the KML
    gt = raster.GetGeoTransform()
    coordStr = ('%.4f,%.4f %.4f,%.4f %.4f,%.4f %.4f,%.4f' %
      (gt[0], gt[3]+raster.RasterYSize*gt[5], gt[0]+raster.RasterXSize*gt[1],
        gt[3]+raster.RasterYSize*gt[5], gt[0]+raster.RasterXSize*gt[1], gt[3],
        gt[0], gt[3]))

    # Take care of namespaces
    prefix = {}
    gx = '{http://www.google.com/kml/ext/2.2}'
    prefix['gx'] = gx
    ns_gx = {'gx' : 'http://www.google.com/kml/ext/2.2'}
    ns_main = { None : 'http://www.opengis.net/kml/2.2'}
    ns = dict(list(ns_main.items()) + list(ns_gx.items()))

    # Fill in the tree structure
    kmlFile = outFile.replace(orgExt, '.kml')
    kml = et.Element('kml', nsmap=ns)
    overlay = et.SubElement(kml, 'GroundOverlay')
    et.SubElement(overlay, 'name').text = \
      os.path.basename(kmlFile).replace('.kml', '') + ' overlay'
    icon = et.SubElement(overlay, 'Icon')
    et.SubElement(icon, 'href').text = os.path.basename(pngFile)
    et.SubElement(icon, 'viewBoundScale').text = '0.75'
    latLonQuad = et.SubElement(overlay, '{0}LatLonQuad'.format(gx))
    et.SubElement(latLonQuad, 'coordinates').text = coordStr
    with open(kmlFile, 'wb') as outF:
      outF.write(et.tostring(kml, xml_declaration=True, encoding='utf-8',
        pretty_print=True))

    # Zip PNG and KML together - need to be in the directory where the files are
    # in order to remove any path issues...
    back = os.getcwd()
    path = os.path.dirname(outFile)
    if path  != '':
        os.chdir(path)
    zipFile = os.path.basename(outFile.replace(orgExt, '.kmz'))
    zip = zipfile.ZipFile(zipFile, 'w', zipfile.ZIP_DEFLATED)
    zip.write(os.path.basename(kmlFile))
    zip.write(os.path.basename(pngFile))
    zip.close()
    os.chdir(back)

    # Clean up - remove temporary GeoTIFF, KML and PNG
    os.remove(tmpFile)
    os.remove(pngFile)
    os.remove(pngFile + '.aux.xml')
    os.remove(kmlFile)
    if rgbFile is not None:
      os.remove(rgbFile)

  if resampleFile is not None:
    for myfile in glob.glob("{0}*".format(resampleFile)):
      os.remove(myfile)
    
  if resampleFile2 is not None:
    for myfile in glob.glob("{0}*".format(resampleFile2)):
      os.remove(myfile)


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('geotiff', help='name of GeoTIFF file (input)')
    parser.add_argument('width', help='target width (input)')
    parser.add_argument('format', help='output format: GeoTIFF, JPEG, PNG, KML')
    parser.add_argument('output', help='name of output file (output)')
    args = parser.parse_args()

    if not os.path.exists(args.geotiff):
        parser.error(f'GeoTIFF file {args.geotiff} does not exist!')
    if not os.path.splitext(args.output)[-1]:
        parser.error(f'Output file {args.output} does not have an extension!')

    resample_geotiff(args.geotiff, args.width, args.format, args.output)


if __name__ == '__main__':
    main()

