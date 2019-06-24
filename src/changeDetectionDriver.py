#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
import lxml.etree as et
import configparser
import yaml
from datetime import datetime, timedelta
from run_sacd import sacdRTC
import numpy as np
from point2aoiShape import point2aoiShape
from geotiff2time_series import geotiff2time_series
from time_series_trend import time_series_trend
from runChangePoint import runChangePoint
from extractNetcdfTime import extractNetcdfTime
from changePoint2shape import changePoint2shape
from changeDetectionMetadata import changeDetectionMetadata


def addProcessingStep(xmlFile, procStep):

  ### Read existing processing XML file
  parser = et.XMLParser(remove_blank_text=True)
  doc = et.parse(xmlFile, parser)
  statement = doc.xpath('/processing/statement')[0].text
  stepCount = int(doc.xpath('count(//step)'))

  ### Construct existing structure
  proc = et.Element('processing')
  et.SubElement(proc, 'statement').text = statement
  for ii in range(stepCount):
    stepID = doc.xpath('/processing/step[{0}]/@id'.format(ii+1))[0]
    description = \
      doc.xpath('/processing/step[{0}]/description'.format(ii+1))[0].text
    tool = doc.xpath('/processing/step[{0}]/tool'.format(ii+1))[0].text
    start = doc.xpath('/processing/step[{0}]/start'.format(ii+1))[0].text
    stop = doc.xpath('/processing/step[{0}]/stop'.format(ii+1))[0].text
    inputs = doc.xpath('/processing/step[{0}]/input'.format(ii+1))[0].text
    outputs = doc.xpath('/processing/step[{0}]/output'.format(ii+1))[0].text
    step = et.SubElement(proc, 'step', id=stepID)
    et.SubElement(step, 'description').text = description
    et.SubElement(step, 'tool').text = tool
    et.SubElement(step, 'start').text = start
    et.SubElement(step, 'stop').text = stop
    et.SubElement(step, 'input').text = inputs
    et.SubElement(step, 'output').text = outputs

  ### Add processing step
  step = et.SubElement(proc, 'step', id=procStep['id'])
  et.SubElement(step, 'description').text = procStep['description']
  et.SubElement(step, 'tool').text = procStep['tool']
  et.SubElement(step, 'start').text = procStep['start']
  et.SubElement(step, 'stop').text = procStep['stop']
  et.SubElement(step, 'input').text = procStep['input']
  et.SubElement(step, 'output').text = procStep['output']

  ### Write XML file
  with open(xmlFile, 'w') as outF:
    outF.write("<?xml version='1.0' encoding='utf8'?>\n")
    outF.write(et.tostring(proc, encoding='unicode', pretty_print=True))
  outF.close()


def initializeProcessingXML(xmlFile):

  ### Setting up processing XML file
  proc = et.Element('processing')
  et.SubElement(proc, 'statement').text = 'Complete processing flow from a ' \
    'list of time series granules to change detection results'

  ### Write XML file
  with open(xmlFile, 'w') as outF:
    outF.write("<?xml version='1.0' encoding='utf8'?>\n")
    outF.write(et.tostring(proc, encoding='unicode', pretty_print=True))
  outF.close()


def processingStep(xmlFile):

  ### Read existing processing XML file
  parser = et.XMLParser(remove_blank_text=True)
  doc = et.parse(xmlFile, parser)
  stepCount = int(doc.xpath('count(//step)'))
  if stepCount == 0:
    stepID = 'NA'
  else:
    for ii in range(stepCount):
      stepID = doc.xpath('/processing/step[{0}]/@id'.format(ii+1))[0]

  return stepID


def changeDetectionDriver(configFile, restart, init):

  ### Initialize configuration file and YAML metadata file (if requested)
  if init != None:
    (configFile, yamlFile) = init

    ## Gnerate configuration file
    config = configparser.ConfigParser()
    config['General'] = {'output directory':'<TBD>'}
    config['AOI'] = {'width':'1024', 'height':'1024', 'pixel size':'10.0',
      'latitude':'<lat>', 'longitude':'<lon>'}
    config['Stack'] = {'noise floor':'0.001', 'metadata':yamlFile,
      'file list':'<TBD>'}
    config['Change point'] = {'threshold':'0.5', 'iterations':'2000'}
    config['Keep'] = {'aoi shapefile':'yes', 'original time series file':'yes',
      'time series residuals file':'yes', 'timestamps file':'yes',
      'change point mask raster':'yes', 'change point mask vector':'yes',
      'change detection processing file':'yes'}
    with open(configFile, 'w') as cfgFile:
      config.write(cfgFile)

    ## Generate YAML file
    meta = {'global':{'institution':'Alaska Satellite Facility (ASF)',
      'title':'<TBD>', 'source':'Sentinel-1 RTC products', 'comment':
      'Contains modified Copernicus Sentinel data processed by ESA and ASF',
      'reference':'Documentation available at: www.asf.alaska.edu'},
      'data':{'longName':'powerscale value', 'units':'none', 'noData':'nan'}}
    with open(yamlFile, 'w') as yFile:
      yaml.dump(meta, yFile, default_flow_style=False)

    sys.exit(1)

  ### Read auxiliary information from configuration file into a dictionary
  print('Checking information in the configuration file ({0})'\
    .format(os.path.basename(configFile)))
  config = configparser.ConfigParser()
  config.optionxform = str
  config.read(configFile)
  outDir = config['General']['output directory']
  meta = {}
  meta['aoi_height'] = int(config['AOI']['height'])
  meta['aoi_width'] = int(config['AOI']['width'])
  meta['aoi_pixelSize'] = float(config['AOI']['pixel size'])
  meta['aoi_lat'] = float(config['AOI']['latitude'])
  meta['aoi_lon'] = float(config['AOI']['longitude'])
  meta['stack_noiseFloor'] = float(config['Stack']['noise floor'])
  meta['stack_metadata'] = config['Stack']['metadata']
  meta['stack_fileList'] = config['Stack']['file list']
  meta['change_threshold'] = float(config['Change point']['threshold'])
  meta['change_iterations'] = int(config['Change point']['iterations'])

  ### Set up processing steps
  steps = ['AOI shapefile','AOI stack','trend removal','change point raster',
    'change point vector']

  ### Set up output directory
  outDir = os.path.abspath(outDir)
  if not os.path.exists(outDir):
    os.makedirs(outDir)

  ### Initialize processing XML file
  xmlFile = os.path.join(outDir, 'changeDetectionProcessing.xml')
  index = -1
  if not os.path.exists(xmlFile) or restart == True:
    initializeProcessingXML(xmlFile)
  if os.path.exists(xmlFile):
    stepID = processingStep(xmlFile)
    if stepID != 'NA':
      index = steps.index(stepID)

  ### Assign file names
  aoiFile = os.path.join(outDir, 'aoi.shp')
  netcdfFile = os.path.join(outDir, 'timeSeriesAOI.nc')
  residualsFile = os.path.join(outDir, 'timeSeriesResiduals.nc')
  changePointBase = os.path.join(outDir, 'changePoint')
  confidenceFile = changePointBase + '_confidenceLevel.tif'
  changeTimeFile = changePointBase + '_changeTime.tif'
  timeFile = os.path.join(outDir, 'timestamps.csv')
  maskBase = os.path.join(outDir, 'mask')
  changePointShape = changePointBase + '.shp'

  if index < 0:

    ### Generating the AOI shapefile
    print('Generating the AOI shapefile ...')
    procStep = {}
    procStep['id'] = 'AOI shapefile'
    procStep['description'] = \
      'Generation of shapefile defining the area of interest (AOI)'
    procStep['tool'] = 'point2aoiShape'
    procStep['start'] = datetime.utcnow().isoformat() + 'Z'
    procStep['input'] = ('center point - lat: %.4lf, lon: %.4lf; width: %d; ' \
      'height: %d' % (meta['aoi_lat'], meta['aoi_lon'], meta['aoi_width'],
      meta['aoi_height']))
    procStep['output'] = os.path.basename(aoiFile)
    point2aoiShape(meta['aoi_lat'], meta['aoi_lon'], meta['aoi_height'],
      meta['aoi_width'], meta['aoi_pixelSize'], aoiFile)
    procStep['stop'] = datetime.utcnow().isoformat() + 'Z'
    addProcessingStep(xmlFile, procStep)

  if index < 1:

    ### Building time series stack
    print('Building time series AOI stack ...')
    procStep = {}
    procStep['id'] = 'AOI stack'
    procStep['description'] = 'Generation of AOI time series stack'
    procStep['tool'] = 'geotiff2time_series'
    procStep['start'] = datetime.utcnow().isoformat() + 'Z'
    procStep['input'] = os.path.basename(meta['stack_fileList'])
    procStep['output'] = os.path.basename(netcdfFile)
    geotiff2time_series(meta['stack_fileList'], 0, None, None, None, aoiFile,
      None, netcdfFile, meta['stack_metadata'], meta['stack_noiseFloor'], None)
    procStep['stop'] = datetime.utcnow().isoformat() + 'Z'
    addProcessingStep(xmlFile, procStep)

  if index < 2:

    ### Removing trend from time series
    print('Removing trend from time series ...')
    procStep = {}
    procStep['id'] = 'trend removal'
    procStep['description'] = 'Time series trend removal'
    procStep['tool'] = 'time_series_trend'
    procStep['start'] = datetime.utcnow().isoformat() + 'Z'
    procStep['input'] = os.path.basename(netcdfFile)
    procStep['output'] = os.path.basename(residualsFile)
    time_series_trend(netcdfFile, residualsFile)
    procStep['stop'] = datetime.utcnow().isoformat() + 'Z'
    addProcessingStep(xmlFile, procStep)

  if index < 3:

    ### Performing change point analysis
    print('Performing change point analysis ...')
    procStep = {}
    procStep['id'] = 'change point raster'
    procStep['description'] = 'Change point analysis'
    procStep['tool'] = 'runChangePoint'
    procStep['start'] = datetime.utcnow().isoformat() + 'Z'
    procStep['input'] = os.path.basename(residualsFile)
    procStep['output'] = ('Confidence level: %s, change time: %s' %
      (os.path.basename(confidenceFile), os.path.basename(changeTimeFile)))
    runChangePoint(residualsFile, changePointBase, meta['change_iterations'])
    procStep['stop'] = datetime.utcnow().isoformat() + 'Z'
    addProcessingStep(xmlFile, procStep)

  if index < 4:

    ### Exporting change point analysis results to shapefile
    print('Exporting change point analysis results to shapefile ...')
    procStep = {}
    procStep['id'] = 'change point vector'
    procStep['description'] = 'Export change point result to shapefile'
    procStep['tool'] = 'changePoint2shape'
    procStep['start'] = datetime.utcnow().isoformat() + 'Z'
    procStep['input'] = ('Confidence level: %s, change time: %s' %
      (os.path.basename(confidenceFile), os.path.basename(changeTimeFile)))
    procStep['output'] = os.path.basename(changePointShape)
    extractNetcdfTime(residualsFile, timeFile)
    changePoint2shape(confidenceFile, changeTimeFile, timeFile,
      meta['change_threshold'], maskBase, changePointShape)
    procStep['stop'] = datetime.utcnow().isoformat() + 'Z'
    addProcessingStep(xmlFile, procStep)

  ### Generate metadata
  metaFile = os.path.join(outDir, 'changeDetectionMetadata.xml')
  changeDetectionMetadata(configFile, xmlFile, metaFile)

  ### Clean up intermediate files
  if config['Keep']['aoi shapefile'] == 'no':
    if os.path.exists(os.path.join(outDir, 'aoi.dbf')) == True:
      os.remove(os.path.join(outDir, 'aoi.dbf'))
    if os.path.exists(os.path.join(outDir, 'aoi.prj')) == True:
      os.remove(os.path.join(outDir, 'aoi.prj'))
    if os.path.exists(os.path.join(outDir, 'aoi.shp')) == True:
      os.remove(os.path.join(outDir, 'aoi.shp'))
    if os.path.exists(os.path.join(outDir, 'aoi.shx')) == True:
      os.remove(os.path.join(outDir, 'aoi.shx'))
  if config['Keep']['original time series file'] == 'no' and \
    os.path.exists(netcdfFile) == True:
    os.remove(netcdfFile)
  if config['Keep']['time series residuals file'] == 'no' and \
    os.path.exists(residualsFile) == True:
    os.remove(residualsFile)
  if config['Keep']['timestamps file'] == 'no' and \
    os.path.exists(timeFile) == True:
    os.remove(timeFile)
  if config['Keep']['change point mask raster'] == 'no' and \
    os.path.exists(os.path.join(outDir, maskBase+'.tif')) == True:
    os.remove(os.path.join(outDir, maskBase+'.tif'))
  if config['Keep']['change point mask vector'] == 'no':
    if os.path.exists(os.path.join(outDir, 'mask.dbf')) == True:
      os.remove(os.path.join(outDir, 'mask.dbf'))
    if os.path.exists(os.path.join(outDir, 'mask.prj')) == True:
      os.remove(os.path.join(outDir, 'mask.prj'))
    if os.path.exists(os.path.join(outDir, 'mask.shp')) == True:
      os.remove(os.path.join(outDir, 'mask.shp'))
    if os.path.exists(os.path.join(outDir, 'mask.shx')) == True:
      os.remove(os.path.join(outDir, 'mask.shx'))
  if config['Keep']['change detection processing file'] == 'no':
    os.remove(xmlFile)


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='changeDetectionDriver',
    description='runs the change detection end to end',
    formatter_class=RawTextHelpFormatter)
  #parser.add_argument('config', metavar='<configuration file>',
  #  help='name of the configuration file containing processing parameters')
  parser.add_argument('-restart', action='store_true', default=False,
    help='restart the processing flow (if processing XML already exists)')
  init = parser.add_mutually_exclusive_group(required=True)
  init.add_argument('-init', action='store', nargs=2, default=None,
    metavar=('<configuration file>','<YAML metadata file>'),
    help='initialize configuration and boilerplate metadata file only')
  init.add_argument('-config', metavar='<configuration file>', action='store',
    default=None, help='name of the configuration file containing ' \
    'processing parameters')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if args.config != None and not os.path.exists(args.config):
    print('Configuration file (%s) does not exist!' % args.config)
    sys.exit(1)

  changeDetectionDriver(args.config, args.restart, args.init)
