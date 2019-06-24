#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
import lxml.etree as et
import configparser
from asf_time_series import *
from datetime import datetime


def changeDetectionMetadata(configFile, procFile, metaFile):

  ### Read information from configuration file
  config = configparser.ConfigParser()
  config.optionxform = str
  config.read(configFile)

  ## Read file list
  fileList = config['Stack']['file list']
  fileNames = [line.rstrip() for line in open(fileList)]

  ## Read timestamps file
  outDir = config['General']['output directory']
  timeFile = os.path.join(outDir, 'timestamps.csv')
  timestamps = [line.rstrip() for line in open(timeFile)]

  ## Extract metadata from time series file
  ncFile = os.path.join(outDir, 'timeSeriesAOI.nc')
  ncMeta = nc2meta(ncFile)
  proj = osr.SpatialReference()
  proj.ImportFromEPSG(ncMeta['epsg'])
  projStr = ('{0}'.format(proj.ExportToWkt()))
  timeCount = ncMeta['timeCount']

  ## Extract statistics from confidence level and change time
  confidenceLevelFile = os.path.join(outDir, 'changePoint_confidenceLevel.tif')
  ds = gdal.Open(confidenceLevelFile)
  confidenceLevelStatistics = ds.GetRasterBand(1).GetStatistics(0,1)
  changePointFile = os.path.join(outDir, 'changePoint_changeTime.tif')
  ds = gdal.Open(changePointFile)
  changePointStatistics = ds.GetRasterBand(1).GetStatistics(0,1)

  ### Calcuate geographic boundaries
  corners = ogr.Geometry(ogr.wkbMultiPoint)
  ul = ogr.Geometry(ogr.wkbPoint)
  ul.AddPoint(float(ncMeta['minX']), float(ncMeta['maxY']))
  corners.AddGeometry(ul)
  ll = ogr.Geometry(ogr.wkbPoint)
  ll.AddPoint(float(ncMeta['minX']), float(ncMeta['minY']))
  corners.AddGeometry(ll)
  ur = ogr.Geometry(ogr.wkbPoint)
  ur.AddPoint(float(ncMeta['maxX']), float(ncMeta['maxY']))
  corners.AddGeometry(ur)
  lr = ogr.Geometry(ogr.wkbPoint)
  lr.AddPoint(float(ncMeta['maxX']), float(ncMeta['minY']))
  corners.AddGeometry(lr)
  inProj = osr.SpatialReference()
  inProj.ImportFromEPSG(ncMeta['epsg'])
  outProj = osr.SpatialReference()
  outProj.ImportFromEPSG(4326)
  transform = osr.CoordinateTransformation(inProj, outProj)
  corners.Transform(transform)
  env = corners.GetEnvelope()

  ### Read processing XML file
  parser = et.XMLParser(remove_blank_text=True)
  doc = et.parse(procFile, parser)
  statement = doc.xpath('/processing/statement')[0].text
  stepCount = int(doc.xpath('count(//step)'))

  ### Construct existing structure
  meta = et.Element('hdf5')
  et.SubElement(meta, 'granule').text = os.path.join(outDir, 'changePoint')
  et.SubElement(meta, 'metadata_creation').text = \
    datetime.utcnow().isoformat() + 'Z'
  data = et.SubElement(meta, 'data')
  timeSeries = et.SubElement(data, 'time_series')
  et.SubElement(timeSeries, 'start_time').text = timestamps[0]
  et.SubElement(timeSeries, 'stop_time').text = timestamps[timeCount-1]
  for ii in range(timeCount):
    et.SubElement(timeSeries, 'image', id='{0}'.format(ii+1)).text = \
      os.path.splitext(os.path.basename(fileNames[ii]))[0]
  metadata = et.SubElement(meta, 'metadata')
  et.SubElement(metadata, 'title').text = ncMeta['title']
  confidenceLevel = et.SubElement(metadata, 'confidence_level_image')
  et.SubElement(confidenceLevel, 'file').text = \
    os.path.basename(os.path.join(outDir, 'changePoint_confidenceLevel.tif'))
  et.SubElement(confidenceLevel, 'width').text = str(ncMeta['cols'])
  et.SubElement(confidenceLevel, 'height').text = str(ncMeta['rows'])
  et.SubElement(confidenceLevel, 'x_spacing').text = str(ncMeta['pixelSize'])
  et.SubElement(confidenceLevel, 'y_spacing').text = str(ncMeta['pixelSize'])
  et.SubElement(confidenceLevel, 'projection_string').text = projStr
  changeTime = et.SubElement(metadata, 'change_time_image')
  et.SubElement(changeTime, 'file').text = \
    os.path.basename(os.path.join(outDir, 'changePoint_changeTime.tif'))
  et.SubElement(changeTime, 'width').text = str(ncMeta['cols'])
  et.SubElement(changeTime, 'height').text = str(ncMeta['rows'])
  et.SubElement(changeTime, 'x_spacing').text = str(ncMeta['pixelSize'])
  et.SubElement(changeTime, 'y_spacing').text = str(ncMeta['pixelSize'])
  et.SubElement(changeTime, 'projection_string').text = projStr
  aoi = et.SubElement(metadata, 'area_of_interest')
  et.SubElement(aoi, 'center_latitude').text = config['AOI']['latitude']
  et.SubElement(aoi, 'center_longitude').text = config['AOI']['longitude']
  et.SubElement(aoi, 'width').text = str(ncMeta['cols'])
  et.SubElement(aoi, 'height').text = str(ncMeta['rows'])
  et.SubElement(aoi, 'pixel_size').text = str(ncMeta['pixelSize'])
  changePoint = et.SubElement(metadata, 'change_point_analysis')
  et.SubElement(changePoint, 'threshold').text = \
    str(config['Change point']['threshold'])
  et.SubElement(changePoint, 'iterations').text = \
    str(config['Change point']['iterations'])
  extent = et.SubElement(meta, 'extent')
  changePointExtent = et.SubElement(extent, 'change_point_analysis')
  et.SubElement(changePointExtent, 'westBoundLongitude').text = str(env[0])
  et.SubElement(changePointExtent, 'eastBoundLongitude').text = str(env[1])
  et.SubElement(changePointExtent, 'northBoundLatitude').text = str(env[3])
  et.SubElement(changePointExtent, 'southBoundLatitude').text = str(env[2])
  statistics = et.SubElement(meta, 'statistics')
  confidenceLevelStats = et.SubElement(statistics, 'confidence_level_image')
  et.SubElement(confidenceLevelStats, 'minimum_value').text = \
    ('%.3lf' % confidenceLevelStatistics[0])
  et.SubElement(confidenceLevelStats, 'maximum_value').text = \
    ('%.3lf' % confidenceLevelStatistics[1])
  et.SubElement(confidenceLevelStats, 'mean_value').text = \
    ('%.4lf' % confidenceLevelStatistics[2])
  et.SubElement(confidenceLevelStats, 'standard_deviation').text = \
    ('%.4lf' % confidenceLevelStatistics[3])
  et.SubElement(confidenceLevelStats, 'percent_valid_values')
  changeTimeStats = et.SubElement(statistics, 'change_time_image')
  et.SubElement(changeTimeStats, 'minimum_value').text = \
    ('%d' % changePointStatistics[0])
  et.SubElement(changeTimeStats, 'maximum_value').text = \
    ('%d' % changePointStatistics[1])
  et.SubElement(changeTimeStats, 'mean_value').text = \
    ('%.1lf' % changePointStatistics[2])
  et.SubElement(changeTimeStats, 'standard_deviation').text = \
    ('%.1lf' % changePointStatistics[3])
  et.SubElement(changeTimeStats, 'percent_valid_values')
  processing = et.SubElement(meta, 'processing')
  for ii in range(stepCount):
    stepID = doc.xpath('/processing/step[{0}]/@id'.format(ii+1))[0]
    description = \
      doc.xpath('/processing/step[{0}]/description'.format(ii+1))[0].text
    tool = doc.xpath('/processing/step[{0}]/tool'.format(ii+1))[0].text
    start = doc.xpath('/processing/step[{0}]/start'.format(ii+1))[0].text
    stop = doc.xpath('/processing/step[{0}]/stop'.format(ii+1))[0].text
    inputs = doc.xpath('/processing/step[{0}]/input'.format(ii+1))[0].text
    outputs = doc.xpath('/processing/step[{0}]/output'.format(ii+1))[0].text
    step = et.SubElement(processing, 'step', id=stepID)
    et.SubElement(step, 'description').text = description
    et.SubElement(step, 'tool').text = tool
    et.SubElement(step, 'start').text = start
    et.SubElement(step, 'stop').text = stop
    et.SubElement(step, 'input').text = inputs
    et.SubElement(step, 'output').text = outputs
  root = et.SubElement(meta, 'root')
  et.SubElement(root, 'institution').text = ncMeta['institution']
  et.SubElement(root, 'title').text = ncMeta['title']
  et.SubElement(root, 'source').text = ncMeta['source']
  et.SubElement(root, 'original_file').text = \
    os.path.basename(os.path.join(outDir, 'timeSeriesAOI.nc'))
  et.SubElement(root, 'comment').text = ncMeta['comment']
  et.SubElement(root, 'reference').text = ncMeta['reference']
  et.SubElement(root, 'history').text = ncMeta['history']

  ### Write XML metadata file
  with open(metaFile, 'w') as outF:
    outF.write("<?xml version='1.0' encoding='utf8'?>\n")
    outF.write(et.tostring(meta, encoding='unicode', pretty_print=True))
  outF.close()


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='changeDetectionMetadata',
    description='generate basic metadata based on configuration and ' \
      'processing information', formatter_class=RawTextHelpFormatter)
  parser.add_argument('config', metavar='<configuration file>',
    help='name of the configuration file (input)')
  parser.add_argument('proc', metavar='<processing file>',
    help='name of the processing XML file (input)')
  parser.add_argument('meta', metavar='<metadata file>',
    help='name of the metadata file (output)')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.config):
    print('Configuration file (%s) does not exist!' % args.config)
    sys.exit(1)
  if not os.path.exists(args.proc):
    print('Processing XML file (%s) does not exist!' % args.proc)
    sys.exit(1)

  changeDetectionMetadata(args.config, args.proc, args.meta)
