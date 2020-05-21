#!/usr/bin/python

import argparse
from argparse import RawTextHelpFormatter
import sys
import os
import lxml.etree as et
from osgeo import gdal, ogr, osr
import zipfile
from asf_geometry import geometry2geojson


def read_locations(zf, annotationFiles, granule):

  if (len(annotationFiles) == 6):
    prodLevel = 'SLC'
    fields = []
    values = []
    field = {}
    field['name'] = 'granule'
    field['type'] = ogr.OFTString
    field['width'] = 30
    fields.append(field)
    field = {}
    field['name'] = 'swath'
    field['type'] = ogr.OFTString
    field['width'] = 5
    fields.append(field)
    field = {}
    field['name'] = 'burst'
    field['type'] = ogr.OFTInteger
    fields.append(field)
    fileCount = 3
  elif (len(annotationFiles) == 2):
    prodLevel = 'GRD'
    fields = []
    values = []
    field = {}
    field['name'] = 'granule'
    field['type'] = ogr.OFTString
    field['width'] = 30
    fields.append(field)
    field = {}
    field['name'] = 'swath'
    field['type'] = ogr.OFTString
    field['width'] = 5
    fields.append(field)
    fileCount = 1

  for ii in range(fileCount):

    meta = et.fromstring(zf.read(annotationFiles[ii]))
    multiPolygon = ogr.Geometry(ogr.wkbMultiPolygon)
    swath = meta.xpath('/product/adsHeader/swath')[0].text
    if prodLevel == 'SLC':
      linesPerBurst = \
        int(meta.xpath('/product/swathTiming/linesPerBurst')[0].text)
      samplesPerBurst = \
        int(meta.xpath('/product/swathTiming/samplesPerBurst')[0].text)
      numberOfBursts = \
        int(meta.xpath('/product/swathTiming/burstList/@count')[0])
      numberOfPoints = int(meta.xpath('/product/geolocationGrid/' \
        'geolocationGridPointList/@count')[0])

      for burst in range(numberOfBursts):
        for point in range(numberOfPoints):
          xml = ('/product/geolocationGrid/geolocationGridPointList/' \
            'geolocationGridPoint[{0}]/line'.format(point+1))
          line = int(meta.xpath(xml)[0].text)
          xml = ('/product/geolocationGrid/geolocationGridPointList/' \
            'geolocationGridPoint[{0}]/pixel'.format(point+1))
          pixel = int(meta.xpath(xml)[0].text)
          xml = ('/product/geolocationGrid/geolocationGridPointList/' \
            'geolocationGridPoint[{0}]/latitude'.format(point+1))
          lat = float(meta.xpath(xml)[0].text)
          xml = ('/product/geolocationGrid/geolocationGridPointList/' \
            'geolocationGridPoint[{0}]/longitude'.format(point+1))
          lon = float(meta.xpath(xml)[0].text)
          if (abs(burst*linesPerBurst-line) < 3) and (pixel == 0):
            lat1 = lat
            lon1 = lon
          elif (abs(burst*linesPerBurst-line) < 3) and \
            (abs(samplesPerBurst-pixel) < 3):
            lat2 = lat
            lon2 = lon
          elif (abs((burst+1)*linesPerBurst-line) < 3) and \
            (abs(samplesPerBurst-pixel) < 3):
            lat3 = lat
            lon3 = lon
          elif (abs((burst+1)*linesPerBurst-line) < 3) and (pixel == 0):
            lat4 = lat
            lon4 = lon

        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint_2D(lon1, lat1)
        ring.AddPoint_2D(lon2, lat2)
        ring.AddPoint_2D(lon3, lat3)
        ring.AddPoint_2D(lon4, lat4)
        ring.AddPoint_2D(lon1, lat1)
        polygon = ogr.Geometry(ogr.wkbPolygon)
        polygon.AddGeometry(ring)
        multiPolygon.AddGeometry(polygon)

        value = {}
        value['granule'] = granule
        value['swath'] = swath
        value['burst'] = burst + 1
        value['geometry'] = polygon
        values.append(value)

    elif prodLevel == 'GRD':
      numberOfSamples = int(meta.xpath('/product/imageAnnotation/' \
        'imageInformation/numberOfSamples')[0].text)
      numberOfLines = int(meta.xpath('/product/imageAnnotation/' \
        'imageInformation/numberOfLines')[0].text)
      numberOfPoints = int(meta.xpath('/product/geolocationGrid/' \
        'geolocationGridPointList/@count')[0])

      ring = ogr.Geometry(ogr.wkbLinearRing)

      for point in range(numberOfPoints):
        xml = ('/product/geolocationGrid/geolocationGridPointList/' \
          'geolocationGridPoint[{0}]/line'.format(point+1))
        line = int(meta.xpath(xml)[0].text)
        xml = ('/product/geolocationGrid/geolocationGridPointList/' \
          'geolocationGridPoint[{0}]/pixel'.format(point+1))
        pixel = int(meta.xpath(xml)[0].text)
        xml = ('/product/geolocationGrid/geolocationGridPointList/' \
          'geolocationGridPoint[{0}]/latitude'.format(point+1))
        lat = float(meta.xpath(xml)[0].text)
        xml = ('/product/geolocationGrid/geolocationGridPointList/' \
          'geolocationGridPoint[{0}]/longitude'.format(point+1))
        lon = float(meta.xpath(xml)[0].text)
        if line == 0 and pixel == 0:
          lon1 = lon
          lat1 = lat
        elif line == 0 and pixel == numberOfSamples-1:
          lon2 = lon
          lat2 = lat
        elif line == numberOfLines-1 and pixel == numberOfSamples-1:
          lon3 = lon
          lat3 = lat
        elif line == numberOfLines-1 and pixel == 0:
          lon4 = lon
          lat4 = lat

      ring.AddPoint_2D(lon1, lat1)
      ring.AddPoint_2D(lon2, lat2)
      ring.AddPoint_2D(lon3, lat3)
      ring.AddPoint_2D(lon4, lat4)
      ring.AddPoint_2D(lon1, lat1)
      polygon = ogr.Geometry(ogr.wkbPolygon)
      polygon.AddGeometry(ring)
      multiPolygon.AddGeometry(polygon)

      value = {}
      value['granule'] = granule
      value['swath'] = swath
      value['geometry'] = polygon
      values.append(value)

  return (fields, values, multiPolygon)


def read_manifest(zf, nameList):

  for name in nameList:
    if 'manifest.safe' in name:
      manifest = name
  (granule, fileName) = os.path.split(manifest)
  meta = et.fromstring(zf.read(manifest))
  multiPolygon = ogr.Geometry(ogr.wkbMultiPolygon)
  fileNames = []
  ids = meta.xpath('//dataObjectSection/dataObject/@ID')
  for id in ids:
    if id.startswith('products1'):
      xml = ('//dataObjectSection/dataObject[@ID="{0}"]/byteStream/' \
        'fileLocation/@href'.format(id))
      file = meta.xpath(xml)[0]
      #print('file: {0}'.format(file))
      for name in nameList:
        #print(name)
        if file[1:] in name:
          fileNames.append(name)

  return (fileNames, granule)


def zipLocation2geojson(inFile, outFile):

  zf = zipfile.ZipFile(inFile, 'r')
  nameList = zf.namelist()
  (fileNames, granule) = read_manifest(zf, nameList)
  (fields, values, multiPolygon) = read_locations(zf, fileNames, granule)
  spatialRef = osr.SpatialReference()
  spatialRef.ImportFromEPSG(4326)
  geometry2geojson(fields, values, spatialRef, False, outFile)


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='zipLocation2shape',
    description='Extracts Sentinel locations and saves them as GeoJSON file',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('inFile', metavar='<zip file>',
    help='name of Sentinel zip file')
  parser.add_argument('outFile', metavar='<GeoJSON file',
    help='name of the GeoJSON file')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  zipLocation2geojson(args.inFile, args.outFile)