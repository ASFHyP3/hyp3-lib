#!/usr/bin/python

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
import lxml.etree as et
import xlsxwriter
from asf_geometry import *

eos = '{http://earthdata.nasa.gov/schema/eos}'
gco = '{http://www.isotc211.org/2005/gco}'
gmd = '{http://www.isotc211.org/2005/gmd}'
gmx = '{http://www.isotc211.org/2005/gmx}'


def geotiff_meta2xls(listFile, xlsFile):

  ### Write metadata to Excel spreadsheet
  outFile = os.path.basename(xlsFile)
  print('Writing information to Excel spreadsheet file (%s) ...' % outFile)
  workbook = xlsxwriter.Workbook(xlsFile)
  worksheet = workbook.add_worksheet('metadata')
  bold = workbook.add_format({'bold':True})
  worksheet.write('A1', 'Granule', bold)
  worksheet.write('B1', 'Acquisition datetime', bold)
  worksheet.write('C1', 'OriginX', bold)
  worksheet.write('D1', 'OriginY', bold)
  worksheet.write('E1', 'Pixel size', bold)
  worksheet.write('F1', 'EPSG', bold)
  worksheet.write('G1', 'Point/Area', bold)
  worksheet.write('H1', 'Rows', bold)
  worksheet.write('I1', 'Columns', bold)
  worksheet.write('J1', 'Range offset', bold)
  worksheet.write('K1', 'Azimuth offset', bold)
  worksheet.write('L1', 'Coregistration', bold)
  worksheet.write('M1', 'Range fit', bold)
  worksheet.write('N1', 'Azimuth fit', bold)

  ### Read the list file: granule, ISO XML metadata
  lines = [line.rstrip('\n') for line in open(listFile)]
  for ii in range(1,len(lines)+1):

    ## Split input in GeoTIFF and XML
    (rasterFile, xmlFile) = lines[ii-1].split(',')

    ## Extract metadata from GeoTIFF file
    (spatialRef, gt, shape, pixel) = raster_meta(rasterFile)
    if spatialRef.GetAttrValue('AUTHORITY', 0) == 'EPSG':
      epsg = int(spatialRef.GetAttrValue('AUTHORITY', 1))
    originX = gt[0]
    originY = gt[3]
    pixelSize = gt[1]
    (rows, cols) = shape

    ## Extract metadata from ISO XML file
    parser = et.XMLParser(remove_blank_text=True)
    doc = et.parse(xmlFile, parser)

    # Granule
    alternateTitles = []
    values = []
    citations = doc.findall('.//{0}CI_Citation'.format(gmd))
    for kk in range(len(citations)):
      for elem in citations[kk].iterdescendants():
        if elem.tag == ('{0}alternateTitle'.format(gmd)):
          alternateTitles.append(elem[0].text)
        if elem.tag == ('{0}title'.format(gmd)) and len(elem) > 0:
          values.append(elem[0].text)
    index = alternateTitles.index('terrain corrected image')
    granule = values[index].replace('.tif','')

    # Center time 
    names = []
    values = []
    addAttributes = doc.findall('.//{0}additionalAttribute'.format(eos))
    for kk in range(len(addAttributes)):
      for elem in addAttributes[kk].iterdescendants():
        if elem.tag == ('{0}name'.format(eos)):
          names.append(elem[0].text)
        if elem.tag == ('{0}value'.format(eos)):
          values.append(elem[0].text)
    index = names.index('center time')
    centerTime = values[index]

    # Range offset, azimuth offset, coregistration, range fit, azimuth fit
    reports = doc.findall('.//{0}report'.format(gmd))
    measures = []
    values = []
    for kk in range(len(reports)):
      for elem in reports[kk].iterdescendants():
        if elem.tag == ('{0}nameOfMeasure'.format(gmd)):
          measures.append(elem[0].text)
        if elem.tag == ('{0}Record'.format(gco)):
          values.append(elem[0].text)
    index = measures.index('coregistration success flag')
    coregistration = values[index]
    index = measures.index('coregistration range offset')
    range_offset = values[index]
    index = measures.index('coregistration azimuth offset')
    azimuth_offset = values[index]
    index = measures.index('final model fit standard deviation in range ' \
      'direction')
    range_fit = values[index]
    index = measures.index('final model fit standard deviation in azimuth ' \
      'direction')
    azimuth_fit = values[index]

    ## Write info to cells
    worksheet.write(ii, 0, granule)
    worksheet.write(ii, 1, centerTime)
    worksheet.write(ii, 2, float(originX))
    worksheet.write(ii, 3, float(originY))
    worksheet.write(ii, 4, float(pixelSize))
    worksheet.write(ii, 5, int(epsg))
    worksheet.write(ii, 6, pixel)
    worksheet.write(ii, 7, int(rows))
    worksheet.write(ii, 8, int(cols))
    worksheet.write(ii, 9, float(range_offset))
    worksheet.write(ii, 10, float(azimuth_offset))
    worksheet.write(ii, 11, coregistration)
    worksheet.write(ii, 12, float(range_fit))
    worksheet.write(ii, 13, float(azimuth_fit))

  workbook.close()


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='geotiff_meta2xls',
    description='Extract metadata from GeoTIFF file and ISO metadata',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('input', metavar='<list file>',
    help='name of the list file with GeoTIFF and XML information')
  parser.add_argument('output', metavar='<Excel file>',
    help='name of the Excel spreadsheet file')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.input):
    print('List file (%s) does not exist!' % args.input)
    sys.exit(1)

  geotiff_meta2xls(args.input, args.output)
