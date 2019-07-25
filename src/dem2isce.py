#!/usr/bin/python

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
import lxml.etree as et
from osgeo import osr, gdal
  
def dem2isce(demFile, hdrFile, xmlFile):

  # Read metadata from the DEM
  raster = gdal.Open(demFile, gdal.GA_ReadOnly)
  if raster is None:
    print('Unable to open DEM file (%s) !' % demFile)
    sys.exit(1)
  print('Converting %s file (%s) ...' % (raster.GetDriver().ShortName, demFile))
  gt = raster.GetGeoTransform()
  band = raster.GetRasterBand(1)
  data_type = gdal.GetDataTypeName(band.DataType)
  proj = osr.SpatialReference()
  proj.ImportFromWkt(raster.GetProjectionRef())
  datum = proj.GetAttrValue('datum')
  lines = [line.rstrip() for line in open(hdrFile)]

  # Build XML tree
  isce = et.Element('component', name='DEM')
  property = et.SubElement(isce, 'property', name='BYTE_ORDER')
  if 'byte order = 0' in lines:
    et.SubElement(property, 'value').text = 'l'
  else:
    et.SubElement(property, 'value').text = 'b'
  property = et.SubElement(isce, 'property', name='ACCESS_MODE')
  et.SubElement(property, 'value').text = 'read'
  property = et.SubElement(isce, 'property', name='REFERENCE')
  if datum == 'WGS_1984':
    et.SubElement(property, 'value').text = 'WGS84'
  elif datum == 'North_American_Datum_1983':
    et.SubElement(property, 'value').text = 'NAD83'
  property = et.SubElement(isce, 'property', name='DATA_TYPE')
  if data_type == 'Int16':
    et.SubElement(property, 'value').text = 'SHORT'
  elif data_type == 'Float32':
    et.SubElement(property, 'value').text = 'FLOAT'
  property = et.SubElement(isce, 'property', name='SCHEME')
  if 'interleave = bsq' in lines:
    et.SubElement(property, 'value').text = 'BSQ'
  elif 'interleave = bil' in lines:
    et.SubElement(property, 'value').text = 'BIL'
  elif 'interleave = bip' in lines:
    et.SubElement(property, 'value').text = 'BIP'
  property = et.SubElement(isce, 'property', name='IMAGE_TYPE')
  et.SubElement(property, 'value').text = 'dem'
  property = et.SubElement(isce, 'property', name='FILE_NAME')
  et.SubElement(property, 'value').text = os.path.abspath(demFile)
  property = et.SubElement(isce, 'property', name='WIDTH')
  et.SubElement(property, 'value').text = str(raster.RasterXSize)
  property = et.SubElement(isce, 'property', name='LENGTH')
  et.SubElement(property, 'value').text = str(raster.RasterYSize)
  property = et.SubElement(isce, 'property', name='NUMBER_BANDS')
  et.SubElement(property, 'value').text = str(raster.RasterCount)
  property = et.SubElement(isce, 'property', name='FIRST_LATITUDE')  
  et.SubElement(property, 'value').text = str(gt[3])
  property = et.SubElement(isce, 'property', name='FIRST_LONGITUDE')
  et.SubElement(property, 'value').text = str(gt[0])
  property = et.SubElement(isce, 'property', name='DELTA_LATITUDE')
  et.SubElement(property, 'value').text = str(gt[5])
  property = et.SubElement(isce, 'property', name='DELTA_LONGITUDE')
  et.SubElement(property, 'value').text = str(gt[1])
  component = et.SubElement(isce, 'component', name='Coordinate1')
  et.SubElement(component, 'factorymodule').text = 'isceobj.Image'
  et.SubElement(component, 'factoryname').text = 'createCoordinate'
  et.SubElement(component, 'doc').text = 'First coordinate of a 2D image (width).'
  property = et.SubElement(component, 'property', name='startingValue')
  et.SubElement(property, 'value').text = str(gt[0])
  et.SubElement(property, 'doc').text = 'Starting value of the coordinate.'
  et.SubElement(property, 'units').text = 'degree'
  property = et.SubElement(component, 'property', name='delta')
  et.SubElement(property, 'value').text = str(gt[1])
  et.SubElement(property, 'doc').text = 'Coordinate quantization.'
  property = et.SubElement(component, 'property', name='size')
  et.SubElement(property, 'value').text = str(raster.RasterXSize)
  et.SubElement(property, 'doc').text = 'Coordinate size.'
  component = et.SubElement(isce, 'component', name='Coordinate2')
  et.SubElement(component, 'factorymodule').text = 'isceobj.Image'
  et.SubElement(component, 'factoryname').text = 'createCoordinate'
  et.SubElement(component, 'doc').text = 'Second coordinate of a 2D image (length).'
  property = et.SubElement(component, 'property', name='startingValue')
  et.SubElement(property, 'value').text = str(gt[3])
  et.SubElement(property, 'doc').text = 'Starting value of the coordinate.'
  et.SubElement(property, 'units').text = 'degree'
  property = et.SubElement(component, 'property', name='delta')
  et.SubElement(property, 'value').text = str(gt[5])
  et.SubElement(property, 'doc').text = 'Coordinate quantization.'
  property = et.SubElement(component, 'property', name='size')
  et.SubElement(property, 'value').text = str(raster.RasterYSize)
  et.SubElement(property, 'doc').text = 'Coordinate size.'
  
  # Write the tree structure to file
  with open(xmlFile, 'wb') as outF:
    outF.write(et.tostring(isce, encoding='UTF-8', xml_declaration=True, 
      pretty_print=True))
  outF.close()
  lines = None


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='dem2isce',
    description='generates an XML file for a DEM for ISCE processing',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('dem', metavar='<dem>',
    help='name of DEM file, assumed to be in ENVI format')
  parser.add_argument('hdr', metavar='<hdr>',
    help='name of the ENVI header file')
  parser.add_argument('xml', metavar='<xml>',
    help='name of XML file')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  dem2isce(args.dem, args.hdr, args.xml)
