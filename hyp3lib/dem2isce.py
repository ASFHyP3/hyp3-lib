"""generates an XML file for a DEM for ISCE processing"""

import argparse
import os

import lxml.etree as et
from osgeo import osr, gdal


def dem2isce(demFile, hdrFile, xmlFile):

  # Read metadata from the DEM
  raster = gdal.Open(demFile, gdal.GA_ReadOnly)
  if raster is None:
    raise FileNotFoundError(f'Unable to open DEM file {demFile} !')
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
  element_property = et.SubElement(isce, 'property', name='BYTE_ORDER')
  if 'byte order = 0' in lines:
    et.SubElement(element_property, 'value').text = 'l'
  else:
    et.SubElement(element_property, 'value').text = 'b'
  element_property = et.SubElement(isce, 'property', name='ACCESS_MODE')
  et.SubElement(element_property, 'value').text = 'read'
  element_property = et.SubElement(isce, 'property', name='REFERENCE')
  if datum == 'WGS_1984':
    et.SubElement(element_property, 'value').text = 'WGS84'
  elif datum == 'North_American_Datum_1983':
    et.SubElement(element_property, 'value').text = 'NAD83'
  element_property = et.SubElement(isce, 'property', name='DATA_TYPE')
  if data_type == 'Int16':
    et.SubElement(element_property, 'value').text = 'SHORT'
  elif data_type == 'Float32':
    et.SubElement(element_property, 'value').text = 'FLOAT'
  element_property = et.SubElement(isce, 'property', name='SCHEME')
  if 'interleave = bsq' in lines:
    et.SubElement(element_property, 'value').text = 'BSQ'
  elif 'interleave = bil' in lines:
    et.SubElement(element_property, 'value').text = 'BIL'
  elif 'interleave = bip' in lines:
    et.SubElement(element_property, 'value').text = 'BIP'
  element_property = et.SubElement(isce, 'property', name='IMAGE_TYPE')
  et.SubElement(element_property, 'value').text = 'dem'
  element_property = et.SubElement(isce, 'property', name='FILE_NAME')
  et.SubElement(element_property, 'value').text = os.path.abspath(demFile)
  element_property = et.SubElement(isce, 'property', name='WIDTH')
  et.SubElement(element_property, 'value').text = str(raster.RasterXSize)
  element_property = et.SubElement(isce, 'property', name='LENGTH')
  et.SubElement(element_property, 'value').text = str(raster.RasterYSize)
  element_property = et.SubElement(isce, 'property', name='NUMBER_BANDS')
  et.SubElement(element_property, 'value').text = str(raster.RasterCount)
  element_property = et.SubElement(isce, 'property', name='FIRST_LATITUDE')
  et.SubElement(element_property, 'value').text = str(gt[3])
  element_property = et.SubElement(isce, 'property', name='FIRST_LONGITUDE')
  et.SubElement(element_property, 'value').text = str(gt[0])
  element_property = et.SubElement(isce, 'property', name='DELTA_LATITUDE')
  et.SubElement(element_property, 'value').text = str(gt[5])
  element_property = et.SubElement(isce, 'property', name='DELTA_LONGITUDE')
  et.SubElement(element_property, 'value').text = str(gt[1])
  component = et.SubElement(isce, 'component', name='Coordinate1')
  et.SubElement(component, 'factorymodule').text = 'isceobj.Image'
  et.SubElement(component, 'factoryname').text = 'createCoordinate'
  et.SubElement(component, 'doc').text = 'First coordinate of a 2D image (width).'
  element_property = et.SubElement(component, 'property', name='startingValue')
  et.SubElement(element_property, 'value').text = str(gt[0])
  et.SubElement(element_property, 'doc').text = 'Starting value of the coordinate.'
  et.SubElement(element_property, 'units').text = 'degree'
  element_property = et.SubElement(component, 'property', name='delta')
  et.SubElement(element_property, 'value').text = str(gt[1])
  et.SubElement(element_property, 'doc').text = 'Coordinate quantization.'
  element_property = et.SubElement(component, 'property', name='size')
  et.SubElement(element_property, 'value').text = str(raster.RasterXSize)
  et.SubElement(element_property, 'doc').text = 'Coordinate size.'
  component = et.SubElement(isce, 'component', name='Coordinate2')
  et.SubElement(component, 'factorymodule').text = 'isceobj.Image'
  et.SubElement(component, 'factoryname').text = 'createCoordinate'
  et.SubElement(component, 'doc').text = 'Second coordinate of a 2D image (length).'
  element_property = et.SubElement(component, 'property', name='startingValue')
  et.SubElement(element_property, 'value').text = str(gt[3])
  et.SubElement(element_property, 'doc').text = 'Starting value of the coordinate.'
  et.SubElement(element_property, 'units').text = 'degree'
  element_property = et.SubElement(component, 'property', name='delta')
  et.SubElement(element_property, 'value').text = str(gt[5])
  et.SubElement(element_property, 'doc').text = 'Coordinate quantization.'
  element_property = et.SubElement(component, 'property', name='size')
  et.SubElement(element_property, 'value').text = str(raster.RasterYSize)
  et.SubElement(element_property, 'doc').text = 'Coordinate size.'
  
  # Write the tree structure to file
  with open(xmlFile, 'wb') as outF:
    outF.write(et.tostring(isce, encoding='UTF-8', xml_declaration=True, 
      pretty_print=True))
  outF.close()
  lines = None


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('dem', metavar='<dem>',
                        help='name of DEM file, assumed to be in ENVI format')
    parser.add_argument('hdr', metavar='<hdr>',
                        help='name of the ENVI header file')
    parser.add_argument('xml', metavar='<xml>',
                        help='name of XML file')
    args = parser.parse_args()

    dem2isce(args.dem, args.hdr, args.xml)


if __name__ == '__main__':
    main()
