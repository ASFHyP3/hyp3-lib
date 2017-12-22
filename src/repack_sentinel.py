#!/usr/bin/python

import argparse
from argparse import RawTextHelpFormatter
import sys
import os
import shutil
import zipfile
import hashlib
import lxml.etree as et
import copy
from osgeo import gdal, ogr, osr
from asf_geometry import *

gml = '{http://www.opengis.net/gml}'
xfdu = '{urn:ccsds:schema:xfdu:1}'
safe = '{http://www.esa.int/safe/sentinel-1.0}'
s1sarl1 = '{http://www.esa.int/safe/sentinel-1.0/sentinel-1/sar/level-1}'

iw = ['iw1', 'iw2', 'iw3']
ew = ['ew1', 'ew2', 'ew3', 'ew4', 'ew5']


def point_within_polygon(x, y, polygon):

  ring = polygon.GetGeometryRef(0)
  nPoints = ring.GetPointCount()
  inside = False

  p1x, p1y, p1z = ring.GetPoint(0)
  for i in range(nPoints + 1):
    p2x, p2y, p2z = ring.GetPoint(i % nPoints)
    if y > min(p1y, p2y):
      if y <= max(p1y, p2y):
        if x <= max(p1x, p2x):
          if p1y != p2y:
            xInt = (y - p1y)*(p2x - p1x)/(p2y -p1y) + p1x
          if p1x == p2x or x < xInt:
            inside = not inside
    p1x, p1y = p2x, p2y

  return inside


def read_burst_time_locations(annotationFile):

  bursts_time_loc = []
  gcps = []
  parser = et.XMLParser(remove_blank_text=True)
  doc = et.parse(annotationFile, parser)

  linesPerBurst = int(doc.xpath('/product/swathTiming/linesPerBurst')[0].text)
  samplesPerBurst = \
    int(doc.xpath('/product/swathTiming/samplesPerBurst')[0].text)
  numberOfBursts = int(doc.xpath('/product/swathTiming/burstList/@count')[0])
  numberOfPoints = int(doc.xpath('/product/geolocationGrid/'\
    'geolocationGridPointList/@count')[0])

  for b in range(numberOfBursts):
    burst = {}
    burst['number'] = b+1
    xml = ('/product/swathTiming/burstList/burst[{0}]/azimuthTime'\
      .format(b+1))
    burst['time'] = doc.xpath(xml)[0].text
    xml = ('/product/swathTiming/burstList/burst[{0}]/azimuthAnxTime'\
      .format(b+1))
    burst['anxTime'] = doc.xpath(xml)[0].text
    for p in range(numberOfPoints):
      xml = ('/product/geolocationGrid/geolocationGridPointList/'\
        'geolocationGridPoint[{0}]/line'.format(p+1))
      line = int(doc.xpath(xml)[0].text)
      xml = ('/product/geolocationGrid/geolocationGridPointList/'\
        'geolocationGridPoint[{0}]/pixel'.format(p+1))
      pixel = int(doc.xpath(xml)[0].text)
      xml = ('/product/geolocationGrid/geolocationGridPointList/'\
        'geolocationGridPoint[{0}]/latitude'.format(p+1))
      lat = float(doc.xpath(xml)[0].text)
      xml = ('/product/geolocationGrid/geolocationGridPointList/'\
        'geolocationGridPoint[{0}]/longitude'.format(p+1))
      lon = float(doc.xpath(xml)[0].text)
      xml = ('/product/geolocationGrid/geolocationGridPointList/'\
        'geolocationGridPoint[{0}]/height'.format(p+1))
      height = float(doc.xpath(xml)[0].text)
      xml = ('/product/geolocationGrid/geolocationGridPointList/'\
        'geolocationGridPoint[{0}]/azimuthTime'.format(p+1))
      azimuthTime = doc.xpath(xml)[0].text
      if b == 0:
        gcp = {}
        gcp['line'] = line
        gcp['pixel'] = pixel
        gcp['lat'] = lat
        gcp['lon'] = lon
        gcp['height'] = height
        gcp['time'] = azimuthTime
        gcps.append(gcp)
      if (abs(b*linesPerBurst-line) < 3) and (pixel == 0):
        burst['firstLine'] = line
        lat1 = lat
        lon1 = lon
      if (abs(b*linesPerBurst-line) < 3) and (abs(samplesPerBurst-pixel) < 3):
        lat2 = lat
        lon2 = lon
      if (abs((b+1)*linesPerBurst-line) < 3) and \
        (abs(samplesPerBurst-pixel) < 3):
        lat3 = lat
        lon3 = lon
      if (abs((b+1)*linesPerBurst-line) < 3) and (pixel == 0):
        burst['lastLine'] = line
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
    burst['polygon'] = polygon
    bursts_time_loc.append(burst)
    burst = None

  return (bursts_time_loc, gcps)


def md5_check(fileName):

  hash_md5 = hashlib.md5()
  with open(fileName, 'rb') as fp:
    for chunk in iter(lambda: fp.read(4096), b""):
      hash_md5.update(chunk)

  return hash_md5.hexdigest()


def read_manifest(manifestFile):

  # Read manifest file
  path, fileName = os.path.split(manifestFile)
  parser = et.XMLParser(remove_blank_text=True)
  doc = et.parse(manifestFile, parser)

  # Data quality
  '''
  # Some data quality
  print('Checking file sizes and MD5 checksums ...')
  '''
  schema = doc.xpath('.//dataObjectSection/dataObject/@repID')
  size = doc.xpath('.//dataObjectSection/dataObject/byteStream/@size')
  href = \
    doc.xpath('.//dataObjectSection/dataObject/byteStream/fileLocation/@href')
  checksum = \
    doc.xpath('.//dataObjectSection/dataObject/byteStream/checksum')
  '''
  failed = False
  for i in range(len(size)):
    fileName = os.path.join(path, href[i])
    if os.path.isfile(fileName):
      fileSize = os.path.getsize(fileName)
      md5 = md5_check(fileName)
      if checksum[i].text != md5:
        print('MD5 checksum differs - metadata: {0}, disk: {1}'\
          .format(checksum[i].text, md5))
        failed = True
      if int(size[i]) != fileSize:
        print('File size differs - metadata: {0}, disk: {1}'\
          .format(int(size[i]), fileSize))
        failed = True
    else:
      print('File ({0}) does not exist.'.format(href[i]))
  if failed == False:
    print('Data quality passed - File sizes and MD5 checksums are the same.')
  '''

  # Get names for files that need updating
  xml = {}
  annotation = []
  measurement = []
  calibration = []
  noise = []
  for i in range(len(schema)):
    if schema[i] == 's1Level1ProductSchema':
      annotation.append(href[i])
    if schema[i] == 's1Level1MeasurementSchema':
      measurement.append(href[i])
    if schema[i] == 's1Level1CalibrationSchema':
      calibration.append(href[i])
    if schema[i] == 's1Level1NoiseSchema':
      noise.append(href[i])
  xml['annotation'] = annotation
  xml['measurement'] = measurement
  xml['calibration'] = calibration
  xml['noise'] = noise

  return xml


def unzip_granule(granule, zipFile, workDir):

  # Unzipping the data
  print('Extracting Sentinel granule (%s) ...' % zipFile)
  dataDir = os.path.abspath(os.path.join(workDir, 'in'))
  zip = zipfile.ZipFile(zipFile, 'r')
  zip.extractall(dataDir)
  zip.close()
  safeDir = os.path.join(dataDir, granule + '.SAFE')

  return safeDir


def extract_metadata(safeDir):

  # Read manifest file
  print('Extracting metadata ...')
  manifestFile = os.path.join(safeDir, 'manifest.safe')
  xml = read_manifest(manifestFile)

  return xml


def subset_annotation(inFile, outFile, params, stats):

  # Read annotation file
  parser = et.XMLParser(remove_blank_text=True)
  doc = et.parse(inFile, parser)

  # Update times and counts; get a deep copy for refilling later
  doc.xpath('/product/adsHeader/startTime')[0].text = params['startTime']
  doc.xpath('/product/adsHeader/stopTime')[0].text = params['stopTime']
  burstList = doc.xpath('/product/swathTiming/burstList')
  burstList[0].set('count', str(params['numAoiBursts']))
  bursts = doc.xpath('/product/swathTiming/burstList/burst')
  dupBursts = copy.deepcopy(bursts)
  gcpList = doc.xpath('/product/geolocationGrid/geolocationGridPointList')
  gcpList[0].set('count', str(params['numAoiGcps']))
  gcps = doc.xpath('/product/geolocationGrid/geolocationGridPointList/'\
    'geolocationGridPoint')
  dupGcps = copy.deepcopy(gcps)

  # Update burst information
  azimuthTimes = []
  for i in range(params['numBursts']):
    param = ('/product/swathTiming/burstList/burst[%d]/azimuthTime' % (i+1))
    azimuthTime = doc.xpath(param)[0].text
    azimuthTimes.append(azimuthTime)
  for burst in bursts:
    burst.getparent().remove(burst)
  for aoi_burst in params['aoi_bursts']:
    for i in range(params['numBursts']):
      if aoi_burst['time'] == azimuthTimes[i]:
        burstList[0].append(dupBursts[i])
  azimuthTimes = None

  # Update GCP information
  azimuthTimes = []
  for i in range(params['numGcps']):
    param = ('/product/geolocationGrid/geolocationGridPointList/'\
      'geolocationGridPoint[%d]/azimuthTime' % (i+1))
    azimuthTime = doc.xpath(param)[0].text
    azimuthTimes.append(azimuthTime)
  for gcp in gcps:
    gcp.getparent().remove(gcp)
  for aoi_gcp in params['aoi_gcps']:
    for i in range(params['numGcps']):
      if aoi_gcp['time'] == azimuthTimes[i]:
        param = dupGcps[i].xpath('line')
        line = int(param[0].text)
        param[0].text = str(line - params['minLine'])
        gcpList[0].append(dupGcps[i])

  # Update number of lines
  lineCount = params['maxLine'] - params['minLine']
  doc.xpath('/product/imageAnnotation/imageInformation/numberOfLines')\
    [0].text = str(lineCount)

  # Write annotation file
  with open(outFile, 'w') as outF:
    outF.write(et.tostring(doc, xml_declaration=True, encoding='utf-8',
      pretty_print=True))
  outF.close()


def merge_annotation(inFiles, outFile, stats):

  print('annotation: {0}'.format(outFile))
  # Read annotation files; get a deep copy for merged annotation
  docs = []
  n = len(inFiles)
  for k in range(n):
    parser = et.XMLParser(remove_blank_text=True)
    doc = et.parse(inFiles[k], parser)
    docs.append(doc)
  merge = copy.deepcopy(docs[0])

  # Update times and counts; get a deep copy for refilling later
  startTime = docs[0].xpath('/product/adsHeader/startTime')[0].text
  stopTime = docs[n-1].xpath('/product/adsHeader/stopTime')[0].text
  merge.xpath('/product/adsHeader/startTime')[0].text = startTime
  merge.xpath('/product/adsHeader/stopTime')[0].text = stopTime

  # Update burst information
  burstCount = 0
  burstCounts = []
  subBursts = []
  for k in range(n):
    count = int(docs[k].xpath('/product/swathTiming/burstList/@count')[0])
    burstCount += count
    burstCounts.append(count)
    subBurst = docs[k].xpath('/product/swathTiming/burstList/burst')
    subBursts.append(subBurst)
  burstList = merge.xpath('/product/swathTiming/burstList')
  burstList[0].set('count', str(burstCount))
  bursts = merge.xpath('/product/swathTiming/burstList/burst')
  for burst in bursts:
    burst.getparent().remove(burst)
  for k in range(n):
    for i in range(burstCounts[k]):
      burstList[0].append(subBursts[k][i])

  # Update GCP information
  gcpCount = 0
  gcpCounts = []
  subGcps = []
  for k in range(n):
    count = int(doc.xpath('/product/geolocationGrid/' \
      'geolocationGridPointList/@count')[0])
    gcpCount += count
    gcpCounts.append(count)
    subGcp = docs[k].xpath('/product/geolocationGrid/' \
      'geolocationGridPointList/geolocationGridPoint')
    subGcps.append(subGcp)
  gcpList = merge.xpath('/product/geolocationGrid/geolocationGridPointList')
  gcps = merge.xpath('/product/geolocationGrid/' \
    'geolocationGridPointList/geolocationGridPoint')
  for gcp in gcps:
    gcp.getparent().remove(gcp)
  lineOffset = 0
  for k in range(n):
    gcp = subGcps[k][gcpCounts[k]-1]
    lastLine = int(gcp.xpath('line')[0].text)
    for i in range(gcpCounts[k]):
      gcp = subGcps[k][i]
      line = int(gcp.xpath('line')[0].text)
      if line < lastLine:
        gcp.xpath('line')[0].text = str(line + lineOffset)
        gcpList[0].append(gcp)
      elif k == n-1:
        gcp.xpath('line')[0].text = str(line + lineOffset)
        gcpList[0].append(gcp)
      else:
        gcpCount -= 1
    lineOffset += lastLine
  gcpList[0].set('count', str(gcpCount))

  # Update number of lines
  doc.xpath('/product/imageAnnotation/imageInformation/numberOfLines')\
    [0].text = str(lastLine)

  # Write annotation file
  with open(outFile, 'w') as outF:
    outF.write(et.tostring(merge, xml_declaration=True, encoding='utf-8',
      pretty_print=True))
  outF.close()


def subset_calibration(inFile, outFile, params):

  # Read calibration file
  parser = et.XMLParser(remove_blank_text=True)
  doc = et.parse(inFile, parser)

  # Update times; get calibration vectors
  doc.xpath('/calibration/adsHeader/startTime')[0].text = params['startTime']
  doc.xpath('/calibration/adsHeader/stopTime')[0].text = params['stopTime']
  vectorList = doc.xpath('/calibration/calibrationVectorList')
  numVectors = int(vectorList[0].get('count'))
  calVectors = doc.xpath('/calibration/calibrationVectorList/calibrationVector')
  dupVectors = copy.deepcopy(calVectors)

  # Update calibration information
  azimuthTimes = []
  for i in range(numVectors):
    param = ('/calibration/calibrationVectorList/calibrationVector[%d]'\
      '/azimuthTime' % (i+1))
    azimuthTime = doc.xpath(param)[0].text
    azimuthTimes.append(azimuthTime)
  for calVector in calVectors:
    calVector.getparent().remove(calVector)

  numAoiVectors = 0
  for i in range(numVectors):
    if azimuthTimes[i] >= params['startTime'] and \
      azimuthTimes[i] <= params['stopTime']:
      vectorList[0].append(dupVectors[i])
      numAoiVectors += 1
  azimuthTimes = None

  # Update count
  vectorList[0].set('count', str(numAoiVectors))

  # Write calibration file
  with open(outFile, 'w') as outF:
    outF.write(et.tostring(doc, xml_declaration=True, encoding='utf-8',
      pretty_print=True))
  outF.close()


def subset_noise(inFile, outFile, params):

  # Read noise file
  parser = et.XMLParser(remove_blank_text=True)
  doc = et.parse(inFile, parser)

  # Update times; get noise vectors
  doc.xpath('/noise/adsHeader/startTime')[0].text = params['startTime']
  doc.xpath('/noise/adsHeader/stopTime')[0].text = params['stopTime']
  vectorList = doc.xpath('/noise/noiseVectorList')
  numVectors = int(vectorList[0].get('count'))
  noiseVectors = doc.xpath('/noise/noiseVectorList/noiseVector')
  dupVectors = copy.deepcopy(noiseVectors)

  # Update calibration information
  azimuthTimes = []
  for i in range(numVectors):
    param = ('/noise/noiseVectorList/noiseVector[%d]/azimuthTime' % (i+1))
    azimuthTime = doc.xpath(param)[0].text
    azimuthTimes.append(azimuthTime)
  for noiseVector in noiseVectors:
    noiseVector.getparent().remove(noiseVector)

  numAoiVectors = 0
  for i in range(numVectors):
    if azimuthTimes[i] >= params['startTime'] and \
      azimuthTimes[i] <= params['stopTime']:
      vectorList[0].append(dupVectors[i])
      numAoiVectors += 1
  azimuthTimes = None

  # Update count
  vectorList[0].set('count', str(numAoiVectors))

  # Write calibration file
  with open(outFile, 'w') as outF:
    outF.write(et.tostring(doc, xml_declaration=True, encoding='utf-8',
      pretty_print=True))
  outF.close()


def subset_measurement(inFile, outFile, params):

  # Read GeoTIFF
  inRaster = gdal.Open(inFile)
  geotransform = inRaster.GetGeoTransform()
  inBand = inRaster.GetRasterBand(1)
  data = inBand.ReadAsArray()
  minLine = params['minLine']
  maxLine = params['maxLine']
  stats = {}
  stats['im_mean'] = np.mean(data[minLine:maxLine].imag.flatten())
  stats['re_mean'] = np.mean(data[minLine:maxLine].real.flatten())
  stats['im_stdev'] = np.std(data[minLine:maxLine].imag.flatten())
  stats['re_stdev'] = np.std(data[minLine:maxLine].real.flatten())
  cols = inRaster.RasterXSize
  rows = maxLine - minLine
  dataType = inBand.DataType
  outGCPs = []
  inGCPs = inRaster.GetGCPs()
  for gcp in inGCPs:
    if gcp.GCPLine >= minLine and gcp.GCPLine <= maxLine:
      gcp.GCPLine -= minLine
      outGCPs.append(gcp)

  # Write subset GeoTIFF
  driver = gdal.GetDriverByName('GTiff')
  outRaster = driver.Create(outFile, cols, rows, 1, dataType, ['COMPESS=LZW'])
  outRaster.SetGCPs(outGCPs, inRaster.GetGCPProjection())
  outBand = outRaster.GetRasterBand(1)
  outBand.WriteArray(data[minLine:maxLine,:])
  outBand.FlushCache()

  return stats


def merge_measurement(inFiles, outFile):

  # Read GeoTIFFs
  data = []
  rows = 0
  for inFile in inFiles:
    inRaster = gdal.Open(inFile)
    geotransform = inRaster.GetGeoTransform()
    inBand = inRaster.GetRasterBand(1)
    data.append(inBand.ReadAsArray())
    cols = inRaster.RasterXSize
    rows += inRaster.RasterYSize
    dataType = inBand.DataType
    '''
    outGCPs = []
    inGCPs = inRaster.GetGCPs()
    for gcp in inGCPs:
      if gcp.GCPLine >= minLine and gcp.GCPLine <= maxLine:
        gcp.GCPLine -= minLine
        outGCPs.append(gcp)
    '''
  # Merge data
  minLine = 0
  #print('dataType: {0}'.format(dataType))
  merge = np.zeros((rows+1, cols+1), 
    dtype=np.dtype([('re', np.int16), ('im', np.int16)]))
  for i in range(len(inFiles)):
    (cols, rows) = data[i].shape
    maxLine = minLine + rows - 1
    merge[:,minLine:maxLine] = data[i]
    minLine += rows

  # Calculate statistics
  stats = {}
  stats['im_mean'] = np.mean(merge.imag.flatten())
  stats['re_mean'] = np.mean(merge.real.flatten())
  stats['im_stdev'] = np.std(merge.imag.flatten())
  stats['re_stdev'] = np.std(merge.real.flatten())

  # Write merged GeoTIFF
  driver = gdal.GetDriverByName('GTiff')
  outRaster = driver.Create(outFile, cols, rows, 1, dataType, ['COMPESS=LZW'])
  #outRaster.SetGCPs(outGCPs, inRaster.GetGCPProjection())
  outBand = outRaster.GetRasterBand(1)
  outBand.WriteArray(merge)
  outBand.FlushCache()

  return stats


def subset_manifest(inFile, outFile, times, aoiSwaths, corners):

  # Read manifest file
  parser = et.XMLParser(remove_blank_text=True)
  doc = et.parse(inFile, parser)

  # Update swath information
  param = ('.//{0}swath'.format(s1sarl1))
  swaths = doc.findall(param)
  for swath in swaths:
    if swath.text.lower() not in aoiSwaths:
      swath.getparent().remove(swath)

  # Update coordinates
  param = ('.//{0}coordinates'.format(gml))
  coords = doc.find(param)
  coords.text = corners

  # Read information package map
  param = (".//{0}contentUnit[@unitType='SAFE Archive Information Package']"\
    .format(xfdu))
  informationPackageMap = doc.findall(param)
  param = (".//{0}contentUnit[@unitType='SAFE Archive Information Package']/"\
    "{0}contentUnit".format(xfdu))
  contentUnits = doc.findall(param)
  dupContents = copy.deepcopy(contentUnits)
  for contentUnit in contentUnits:
    contentUnit.getparent().remove(contentUnit)

  # Read metadata section
  metaSection = doc.xpath('.//metadataSection')
  metaObjects = doc.xpath('.//metadataSection/metadataObject')
  dupMetaObjects = copy.deepcopy(metaObjects)
  for metaObject in metaObjects:
    metaObject.getparent().remove(metaObject)

  # Read data object section
  dataObjectSection = doc.xpath('.//dataObjectSection')
  dataObjects = doc.xpath('.//dataObjectSection/dataObject')
  dupDataObjects = copy.deepcopy(dataObjects)
  for dataObject in dataObjects:
    dataObject.getparent().remove(dataObject)

  # Track data object IDs through the various structures
  outPath, manifest = os.path.split(outFile)
  for dupDataObject in dupDataObjects:

    # Update data object section: file name and sizes, checksums, IDs
    href = dupDataObject.xpath('byteStream/fileLocation/@href')[0]
    dataObjectID = dupDataObject.get('ID')
    fileName = os.path.join(outPath, href)
    if os.path.isfile(fileName):
      fileSize = os.path.getsize(fileName)
      md5 = md5_check(fileName)
      for time in times:
        check = '-'+time['swath']+'-'
        if check in href:
          oldStart = \
            (time['oldStart'][:19]).replace('-','').replace(':','').lower()
          newStart = \
            (time['newStart'][:19]).replace('-','').replace(':','').lower()
          oldStop = \
            (time['oldStop'][:19]).replace('-','').replace(':','').lower()
          newStop = \
            (time['newStop'][:19]).replace('-','').replace(':','').lower()
      newHref = href.replace(oldStart, newStart).replace(oldStop, newStop)
      fileLocation = dupDataObject.xpath('byteStream/fileLocation')
      fileLocation[0].set('href', newHref)
      newFile = fileName.replace(oldStart, newStart).replace(oldStop, newStop)
      byteStream = dupDataObject.xpath('byteStream')
      byteStream[0].xpath('checksum')[0].text = md5
      byteStream[0].set('size', str(fileSize))
      dataObjectSection[0].append(dupDataObject)

      newFile = fileName.replace(oldStart, newStart).replace(oldStop, newStop)
      os.rename(fileName, newFile)

      # Update information package map
      for dupContent in dupContents:
        dataObj = dupContent.xpath('dataObjectPointer')
        dataObjID = dataObj[0].get('dataObjectID')
        if dataObjID == dataObjectID:
          id = \
            dataObjID.replace(oldStart, newStart).replace(oldStop, newStop)
          dataObj[0].set('dataObjectID', id)
          informationPackageMap[0].append(dupContent)

      # Update metadata section
      for dupMetaObject in dupMetaObjects:
        dataObj = dupMetaObject.xpath('dataObjectPointer')
        if len(dataObj) == 0:
          metaSection[0].append(dupMetaObject)
        else:
          dataObjID = dataObj[0].get('dataObjectID')
          if dataObjID == dataObjectID:
            id = dupMetaObject.get('ID')
            id = id.replace(oldStart, newStart).replace(oldStop, newStop)
            dupMetaObject.set('ID', id)
            id = \
              dataObjID.replace(oldStart, newStart).replace(oldStop, newStop)
            dataObj[0].set('dataObjectID', id)
            metaSection[0].append(dupMetaObject)

      id = dataObjectID.replace(oldStart, newStart).replace(oldStop, newStop)
      dupDataObject.set('ID', id)

  # Write manifest file
  with open(outFile, 'w') as outF:
    outF.write(et.tostring(doc, xml_declaration=True, encoding='utf-8',
      pretty_print=True))
  outF.close()


def subset_granule(zipFile, aoiMultipolygon, workDir):

  # Set up directory structure
  path, granuleZip = os.path.split(zipFile)
  granule = os.path.basename(os.path.splitext(granuleZip)[0])
  print('Subsetting {0} ...'.format(granule))
  dataDir = os.path.abspath(os.path.join(workDir, 'in'))
  safeDir = os.path.join(dataDir, granule + '.SAFE')
  outDir = os.path.abspath(os.path.join(workDir, 'out'))
  if not os.path.isdir(outDir):
    os.makedirs(outDir)
  subDir = os.path.join(outDir, 'annotation')
  if not os.path.isdir(subDir):
    os.makedirs(subDir)
  subDir = os.path.join(outDir, 'annotation', 'calibration')
  if not os.path.isdir(subDir):
    os.makedirs(subDir)
  subDir = os.path.join(outDir, 'measurement')
  if not os.path.isdir(subDir):
    os.makedirs(subDir)
  subDir = os.path.join(outDir, 'preview')
  if not os.path.isdir(subDir):
    os.makedirs(subDir)

  # Unzip granule zip file
  safeDir = unzip_granule(granule, zipFile, workDir)

  # Extract metadata from manifest: annotation files etc.
  meta = extract_metadata(safeDir)
  annotation = meta['annotation']
  measurement = meta['measurement']
  calibration = meta['calibration']
  noise = meta['noise']

  # Extract information from granule name
  mission = granule[0:3].lower()
  mode = granule[4:6]
  if mode == 'IW':
    swaths = iw
  elif mode == 'EW':
    swaths = ew
  aoiSwaths = copy.deepcopy(swaths)
  productType = granule[7:10].lower()
  polarization = granule[14:16]

  # Filter burst and geolocation information
  print('Filtering burst and geolocation information ...')
  times = []
  minLatPt = maxLatPt = ogr.Geometry(ogr.wkbPoint)
  minLonPt = maxLonPt = ogr.Geometry(ogr.wkbPoint)
  minLat = minLon = 999
  maxLat = maxLon = -999
  minTime = ('{0}-{1}-{2}:{3}:{4}'.format(granule[33:37], granule[37:39],
    granule[39:44], granule[44:46], granule[46:48]))
  maxTime = ('{0}-{1}-{2}:{3}:{4}'.format(granule[17:21], granule[21:23],
    granule[23:28], granule[28:30], granule[30:32]))

  # Loop through the swaths
  for swath in swaths:

    # Extract burst and GCP information per swath
    if polarization == 'DV' or polarization == 'SV':
      start = ('./annotation/{0}-{1}-{2}-vv'.format(mission, swath,
        productType))
    elif polarization == 'DH' or polarization == 'SH':
      start = ('./annotation/{0}-{1}-{2}-hh'.format(mission, swath,
        productType))
    for i in range(len(annotation)):
      if annotation[i].startswith(start):
        annotationFile = os.path.join(safeDir, annotation[i])
    bursts, gcps = read_burst_time_locations(annotationFile)
    params = {}
    params['numBursts'] = len(bursts)
    params['numGcps'] = len(gcps)

    # Get start and stop times
    parser = et.XMLParser(remove_blank_text=True)
    doc = et.parse(annotationFile, parser)
    params['startTime'] = doc.xpath('/product/adsHeader/startTime')[0].text
    params['stopTime'] = doc.xpath('/product/adsHeader/stopTime')[0].text
    time = {}
    time['swath'] = swath
    time['oldStart'] = params['startTime']
    time['oldStop'] = params['stopTime']

    # Get image dimensions
    if polarization == 'DV' or polarization == 'SV':
      start = ('./measurement/{0}-{1}-{2}-vv'.format(mission, swath,
        productType))
    elif polarization == 'DH' or polarization == 'SH':
      start = ('./measurement/{0}-{1}-{2}-hh'.format(mission, swath,
        productType))
    for i in range(len(measurement)):
      if measurement[i].startswith(start):
        imageFile = os.path.join(safeDir,measurement[i])

    # Figure out which bursts intersect with the area of interest
    aoi_bursts = []
    for burst in bursts:
      burstPolygon = burst['polygon']
      intersection = aoiMultipolygon.Intersection(burstPolygon)
      if intersection.GetGeometryName() == 'POLYGON':
        aoi_bursts.append(burst)
    params['aoi_bursts'] = aoi_bursts

    # Determine first and last image line
    params['numAoiBursts'] = len(aoi_bursts)
    if len(aoi_bursts) == 0:
      aoiSwaths.remove(swath)
      continue
    aoi_burst = aoi_bursts[0]
    params['minLine'] = aoi_burst['firstLine']
    params['startTime'] = aoi_burst['time']
    aoi_burst = aoi_bursts[params['numAoiBursts']-1]
    params['maxLine'] = aoi_burst['lastLine']
    if aoi_burst['number'] < params['numBursts']:
      params['stopTime'] = bursts[aoi_burst['number']]['time']
    time['newStart'] = params['startTime']
    time['newStop'] = params['stopTime']
    times.append(time)
    time = None

    if params['startTime'][:19] < minTime:
      minTime = params['startTime'][:19]
    if params['stopTime'][:19] > maxTime:
      maxTime = params['stopTime'][:19]

    # Figure out which GCPs correspond to the filtered bursts
    aoi_gcps = []
    for gcp in gcps:
      if gcp['line'] >= params['minLine'] and gcp['line'] <= params['maxLine']:
        aoi_gcps.append(gcp)
    params['aoi_gcps'] = aoi_gcps
    params['numAoiGcps'] = len(aoi_gcps)

    # Update metadata - loop through annotation and measurement files
    print('Updating metadata and data ({0}) ...'.format(swath.upper()))

    # Full-pol metadata
    if polarization == 'DV' or polarization == 'SV':
      start = ('./measurement/{0}-{1}-{2}-vv'.format(mission, swath,
        productType))
    elif polarization == 'DH' or polarization == 'SH':
      start = ('./measurement/{0}-{1}-{2}-hh'.format(mission, swath,
        productType))
    for i in range(len(measurement)):
      if measurement[i].startswith(start):
        inMeasurementFile = os.path.join(safeDir, measurement[i])
        outMeasurementFile = os.path.join(outDir, measurement[i])
    stats = subset_measurement(inMeasurementFile, outMeasurementFile, params)

    if polarization == 'DV' or polarization == 'SV':
      start = ('./annotation/{0}-{1}-{2}-vv'.format(mission, swath,
        productType))
    elif polarization == 'DH' or polarization == 'SH':
      start = ('./annotation/{0}-{1}-{2}-hh'.format(mission, swath,
        productType))
    for i in range(len(annotation)):
      if annotation[i].startswith(start):
        inAnnotationFile = os.path.join(safeDir, annotation[i])
        outAnnotationFile = os.path.join(outDir, annotation[i])
    subset_annotation(inAnnotationFile, outAnnotationFile, params, stats)

    if polarization == 'DV' or polarization == 'SV':
      start = ('./annotation/calibration/calibration-{0}-{1}-{2}-vv'\
        .format(mission, swath, productType))
    elif polarization == 'DH' or polarization == 'SH':
      start = ('./annotation/calibration/calibration-{0}-{1}-{2}-hh'\
        .format(mission, swath, productType))
    for i in range(len(calibration)):
      if calibration[i].startswith(start):
        inCalibrationFile = os.path.join(safeDir, calibration[i])
        outCalibrationFile = os.path.join(outDir, calibration[i])
    subset_calibration(inCalibrationFile, outCalibrationFile, params)

    if polarization == 'DV' or polarization == 'SV':
      start = ('./annotation/calibration/noise-{0}-{1}-{2}-vv'.format(mission,
        swath, productType))
    elif polarization == 'DH' or polarization == 'SH':
      start = ('./annotation/calibration/noise-{0}-{1}-{2}-hh'.format(mission,
        swath, productType))
    for i in range(len(noise)):
      if noise[i].startswith(start):
        inNoiseFile = os.path.join(safeDir, noise[i])
        outNoiseFile = os.path.join(outDir, noise[i])
    subset_noise(inNoiseFile, outNoiseFile, params)

    # Cross-pol metadata (if needed)
    if polarization == 'DV' or polarization == 'DH':

      if polarization == 'DV':
        start = ('./measurement/{0}-{1}-{2}-vh'.format(mission, swath,
          productType))
      elif polarization == 'DH':
        start = ('./measurement/{0}-{1}-{2}-hv'.format(mission, swath,
          productType))
      for i in range(len(measurement)):
        if measurement[i].startswith(start):
          inMeasurementFile = os.path.join(safeDir, measurement[i])
          outMeasurementFile = os.path.join(outDir, measurement[i])
      stats = subset_measurement(inMeasurementFile, outMeasurementFile, params)

      if polarization == 'DV':
        start = ('./annotation/{0}-{1}-{2}-vh'.format(mission, swath,
          productType))
      elif polarization == 'DH':
        start = ('./annotation/{0}-{1}-{2}-hv'.format(mission, swath,
          productType))
      for i in range(len(annotation)):
        if annotation[i].startswith(start):
          inAnnotationFile = os.path.join(safeDir, annotation[i])
          outAnnotationFile = os.path.join(outDir, annotation[i])
      subset_annotation(inAnnotationFile, outAnnotationFile, params, stats)

      if polarization == 'DV':
        start = ('./annotation/calibration/calibration-{0}-{1}-{2}-vh'\
          .format(mission, swath, productType))
      elif polarization == 'DH':
        start = ('./annotation/calibration/calibration-{0}-{1}-{2}-hv'\
          .format(mission, swath, productType))
      for i in range(len(calibration)):
        if calibration[i].startswith(start):
          inCalibrationFile = os.path.join(safeDir, calibration[i])
          outCalibrationFile = os.path.join(outDir, calibration[i])
      subset_calibration(inCalibrationFile, outCalibrationFile, params)

      if polarization == 'DV':
        start = ('./annotation/calibration/noise-{0}-{1}-{2}-vh'\
          .format(mission, swath, productType))
      elif polarization == 'DH':
        start = ('./annotation/calibration/noise-{0}-{1}-{2}-hv'\
          .format(mission, swath, productType))
      for i in range(len(noise)):
        if noise[i].startswith(start):
          inNoiseFile = os.path.join(safeDir, noise[i])
          outNoiseFile = os.path.join(outDir, noise[i])
      subset_noise(inNoiseFile, outNoiseFile, params)


    for burst in bursts:
      polygon = burst['polygon']
      ring = polygon.GetGeometryRef(0)
      for i in range(0, ring.GetPointCount()):
        (lon, lat, height) = ring.GetPoint(i)
        if lat < minLat:
          minLatPt = ring.GetPoint(i)
          minLat = lat
        elif lat > maxLat:
          maxLatPt = ring.GetPoint(i)
          maxLat = lat
        elif lon < minLon:
          minLonPt = ring.GetPoint(i)
          minLon = lon
        elif lon > maxLon:
          maxLonPt = ring.GetPoint(i)
          maxLon = lon
  corners = ('{0},{1} {2},{3} {4},{5} {6},{7}'.format(minLatPt[1], minLatPt[0],
    minLonPt[1], minLonPt[0], maxLatPt[1], maxLatPt[0], maxLonPt[1],
    maxLonPt[0]))

  # Update preview

  # Write manifest file
  print('Writing manifest file ...')
  inManifestFile = os.path.join(safeDir, 'manifest.safe')
  outManifestFile = os.path.join(outDir, 'manifest.safe')
  subset_manifest(inManifestFile, outManifestFile, times, aoiSwaths, corners)

  # Calculate CRC16 for manifest

  # Move all annotation and measurement files into output SAFE dir
  print('Moving/Copying files to the new SAFE directory ...')
  outSafeDir = os.path.join(outDir, granule + '.SAFE')
  outSafeDir = \
    outSafeDir.replace(granule[17:32], minTime.replace('-','').replace(':',''))
  outSafeDir = \
    outSafeDir.replace(granule[33:48], maxTime.replace('-','').replace(':',''))
  if not os.path.isdir(outSafeDir):
    os.makedirs(outSafeDir)
  subDir = os.path.join(outSafeDir, 'support')
  if not os.path.isdir(subDir):
    os.makedirs(subDir)
  shutil.move(os.path.join(outDir, 'manifest.safe'),
    os.path.join(outSafeDir, 'manifest.safe'))
  shutil.move(os.path.join(outDir, 'annotation'), outSafeDir)
  shutil.move(os.path.join(outDir, 'measurement'), outSafeDir)
  shutil.move(os.path.join(outDir, 'preview'), outSafeDir)

  # Copy support directory
  supportDir = os.path.join(safeDir, 'support')
  support = [f for f in os.listdir(supportDir)
    if os.path.isfile(os.path.join(supportDir, f))]
  for i in range(len(support)):
    inSupportFile = os.path.join(safeDir, 'support', support[i])
    outSupportFile = os.path.join(outSafeDir, 'support', support[i])
    shutil.copy(inSupportFile, outSupportFile)

  return outSafeDir


def merge_granules(safeDirs, workDir):

  print('Merging {0} granules ...'.format(len(safeDirs)))

  # Determining granule times to assign merged granule name
  times = []
  for safeDir in safeDirs:
    path, granuleSAFE = os.path.split(safeDir)
    granule = os.path.basename(os.path.splitext(granuleSAFE)[0])
    minTime = granule[17:32]
    maxTime = granule[33:48]
    times.append(minTime)
    times.append(maxTime)

  granule = granule.replace(maxTime, max(times))
  granule = granule.replace(minTime, min(times))

  # Set up merge directory structure
  print('Merging into {0} ...'.format(granule))
  outDir = os.path.abspath(os.path.join(workDir, 'final'))
  outSafeDir = os.path.join(outDir, granule + '.SAFE')
  if not os.path.isdir(outSafeDir):
    os.makedirs(outSafeDir)
  subDir = os.path.join(outSafeDir, 'support')
  if not os.path.isdir(subDir):
    os.makedirs(subDir)
  subDir = os.path.join(outSafeDir, 'annotation')
  if not os.path.isdir(subDir):
    os.makedirs(subDir)
  subDir = os.path.join(outSafeDir, 'annotation', 'calibration')
  if not os.path.isdir(subDir):
    os.makedirs(subDir)
  subDir = os.path.join(outSafeDir, 'measurement')
  if not os.path.isdir(subDir):
    os.makedirs(subDir)
  subDir = os.path.join(outSafeDir, 'preview')
  if not os.path.isdir(subDir):
    os.makedirs(subDir)

  # Copy support directory
  supportDir = os.path.join(safeDirs[0], 'support')
  support = [f for f in os.listdir(supportDir)
    if os.path.isfile(os.path.join(supportDir, f))]
  for i in range(len(support)):
    inSupportFile = os.path.join(safeDirs[0], 'support', support[i])
    outSupportFile = os.path.join(outSafeDir, 'support', support[i])
    shutil.copy(inSupportFile, outSupportFile)

  # Extract information from granule name
  mission = granule[0:3].lower()
  mode = granule[4:6]
  if mode == 'IW':
    swaths = iw
  elif mode == 'EW':
    swaths = ew
  productType = granule[7:10].lower()
  polarization = granule[14:16]

  # Loop through the swaths - do not necessary all exist
  for swath in swaths:

    '''
    # Extract burst and GCP information per swath
    if polarization == 'DV' or polarization == 'SV':
      start = ('./annotation/{0}-{1}-{2}-vv'.format(mission, swath,
        productType))
    elif polarization == 'DH' or polarization == 'SH':
      start = ('./annotation/{0}-{1}-{2}-hh'.format(mission, swath,
        productType))
    for i in range(len(annotation)):
      if annotation[i].startswith(start):
        annotationFile = os.path.join(safeDir, annotation[i])
    bursts, gcps = read_burst_time_locations(annotationFile)
    params = {}
    params['numBursts'] = len(bursts)
    params['numGcps'] = len(gcps)

    # Get start and stop times
    parser = et.XMLParser(remove_blank_text=True)
    doc = et.parse(annotationFile, parser)
    params['startTime'] = doc.xpath('/product/adsHeader/startTime')[0].text
    params['stopTime'] = doc.xpath('/product/adsHeader/stopTime')[0].text
    time = {}
    time['swath'] = swath
    time['oldStart'] = params['startTime']
    time['oldStop'] = params['stopTime']

    # Get image dimensions
    if polarization == 'DV' or polarization == 'SV':
      start = ('./measurement/{0}-{1}-{2}-vv'.format(mission, swath,
        productType))
    elif polarization == 'DH' or polarization == 'SH':
      start = ('./measurement/{0}-{1}-{2}-hh'.format(mission, swath,
        productType))
    for i in range(len(measurement)):
      if measurement[i].startswith(start):
        imageFile = os.path.join(safeDir,measurement[i])

    # Figure out which bursts intersect with the area of interest
    aoi_bursts = []
    for burst in bursts:
      burstPolygon = burst['polygon']
      intersection = aoiMultipolygon.Intersection(burstPolygon)
      if intersection.GetGeometryName() == 'POLYGON':
        aoi_bursts.append(burst)
    params['aoi_bursts'] = aoi_bursts

    # Determine first and last image line
    params['numAoiBursts'] = len(aoi_bursts)
    if len(aoi_bursts) == 0:
      aoiSwaths.remove(swath)
      continue
    aoi_burst = aoi_bursts[0]
    params['minLine'] = aoi_burst['firstLine']
    params['startTime'] = aoi_burst['time']
    aoi_burst = aoi_bursts[params['numAoiBursts']-1]
    params['maxLine'] = aoi_burst['lastLine']
    if aoi_burst['number'] < params['numBursts']:
      params['stopTime'] = bursts[aoi_burst['number']]['time']
    time['newStart'] = params['startTime']
    time['newStop'] = params['stopTime']
    times.append(time)
    time = None

    if params['startTime'][:19] < minTime:
      minTime = params['startTime'][:19]
    if params['stopTime'][:19] > maxTime:
      maxTime = params['stopTime'][:19]

    # Figure out which GCPs correspond to the filtered bursts
    aoi_gcps = []
    for gcp in gcps:
      if gcp['line'] >= params['minLine'] and gcp['line'] <= params['maxLine']:
        aoi_gcps.append(gcp)
    params['aoi_gcps'] = aoi_gcps
    params['numAoiGcps'] = len(aoi_gcps)
    '''

    # Full-pol metadata
    if polarization == 'DV' or polarization == 'SV':
      start = ('./measurement/{0}-{1}-{2}-vv'.format(mission, swath,
        productType))
    elif polarization == 'DH' or polarization == 'SH':
      start = ('./measurement/{0}-{1}-{2}-hh'.format(mission, swath,
        productType))
    startTime = []
    stopTime = []
    inMeasurementFiles = []
    for safeDir in safeDirs:
      meta = extract_metadata(safeDir)
      measurement = meta['measurement']
      for i in range(len(measurement)):
        if measurement[i].startswith(start):
          stop = measurement[i][60:]
          inMeasurementFile = os.path.join(safeDir, measurement[i])
          inMeasurementFiles.append(inMeasurementFile)
          startTime.append(os.path.basename(inMeasurementFile)[15:30])
          stopTime.append(os.path.basename(inMeasurementFile)[31:46])
    if len(inMeasurementFiles) > 0:
      newStart = sorted(startTime)
      newStop = sorted(stopTime, reverse=True)
      measurementFile = ('{0}-{1}-{2}-{3}'.format(start, newStart[0],
        newStop[0], stop))
      outMeasurementFile = os.path.join(outSafeDir, measurementFile)
      stats = merge_measurement(inMeasurementFiles, outMeasurementFile)

    if polarization == 'DV' or polarization == 'SV':
      start = ('./annotation/{0}-{1}-{2}-vv'.format(mission, swath,
        productType))
    elif polarization == 'DH' or polarization == 'SH':
      start = ('./annotation/{0}-{1}-{2}-hh'.format(mission, swath,
        productType))
    startTime = []
    stopTime = []
    inAnnotationFiles = []
    for safeDir in safeDirs:
      meta = extract_metadata(safeDir)
      annotation = meta['annotation']
      for i in range(len(annotation)):
        if annotation[i].startswith(start):
          stop = annotation[i][60:]
          inAnnotationFile = os.path.join(safeDir, annotation[i])
          inAnnotationFiles.append(inAnnotationFile)
          startTime.append(os.path.basename(inAnnotationFile)[15:30])
          stopTime.append(os.path.basename(inAnnotationFile)[31:46])
    if len(inAnnotationFiles) > 0:
      newStart = sorted(startTime)
      newStop = sorted(stopTime, reverse=True)
      annotationFile = ('{0}-{1}-{2}-{3}'.format(start, newStart[0],
        newStop[0], stop))
      outAnnotationFile = os.path.join(outSafeDir, annotationFile)
      merge_annotation(inAnnotationFiles, outAnnotationFile, stats)

    '''
      if polarization == 'DV' or polarization == 'SV':
        start = ('./annotation/calibration/calibration-{0}-{1}-{2}-vv'\
          .format(mission, swath, productType))
      elif polarization == 'DH' or polarization == 'SH':
        start = ('./annotation/calibration/calibration-{0}-{1}-{2}-hh'\
          .format(mission, swath, productType))
      for i in range(len(calibration)):
        if calibration[i].startswith(start):
          inCalibrationFile = os.path.join(safeDir, calibration[i])
          outCalibrationFile = os.path.join(outDir, calibration[i])
      subset_calibration(inCalibrationFile, outCalibrationFile, params)

      if polarization == 'DV' or polarization == 'SV':
        start = ('./annotation/calibration/noise-{0}-{1}-{2}-vv'.format(mission,
          swath, productType))
      elif polarization == 'DH' or polarization == 'SH':
        start = ('./annotation/calibration/noise-{0}-{1}-{2}-hh'.format(mission,
          swath, productType))
      for i in range(len(noise)):
        if noise[i].startswith(start):
          inNoiseFile = os.path.join(safeDir, noise[i])
          outNoiseFile = os.path.join(outDir, noise[i])
      subset_noise(inNoiseFile, outNoiseFile, params)
    '''

    # Cross-pol metadata (if needed)
    if polarization == 'DV' or polarization == 'DH':

      stats = None

      if polarization == 'DV':
        start = ('./annotation/{0}-{1}-{2}-vh'.format(mission, swath,
          productType))
      elif polarization == 'DH':
        start = ('./annotation/{0}-{1}-{2}-hv'.format(mission, swath,
          productType))
      startTime = []
      stopTime = []
      inAnnotationFiles = []
      for safeDir in safeDirs:
        meta = extract_metadata(safeDir)
        annotation = meta['annotation']
        for i in range(len(annotation)):
          if annotation[i].startswith(start):
            stop = annotation[i][60:]
            inAnnotationFile = os.path.join(safeDir, annotation[i])
            inAnnotationFiles.append(inAnnotationFile)
            startTime.append(os.path.basename(inAnnotationFile)[15:30])
            stopTime.append(os.path.basename(inAnnotationFile)[31:46])
      if len(inAnnotationFiles) > 0:
        newStart = sorted(startTime)
        newStop = sorted(stopTime, reverse=True)
        annotationFile = ('{0}-{1}-{2}-{3}'.format(start, newStart[0],
          newStop[0], stop))
        outAnnotationFile = os.path.join(outSafeDir, annotationFile)
        merge_annotation(inAnnotationFiles, outAnnotationFile, stats)

      '''
        if polarization == 'DV':
          start = ('./annotation/calibration/calibration-{0}-{1}-{2}-vh'\
            .format(mission, swath, productType))
        elif polarization == 'DH':
          start = ('./annotation/calibration/calibration-{0}-{1}-{2}-hv'\
            .format(mission, swath, productType))
        for i in range(len(calibration)):
          if calibration[i].startswith(start):
            inCalibrationFile = os.path.join(safeDir, calibration[i])
            outCalibrationFile = os.path.join(outDir, calibration[i])
        subset_calibration(inCalibrationFile, outCalibrationFile, params)

        if polarization == 'DV':
          start = ('./annotation/calibration/noise-{0}-{1}-{2}-vh'\
            .format(mission, swath, productType))
        elif polarization == 'DH':
          start = ('./annotation/calibration/noise-{0}-{1}-{2}-hv'\
            .format(mission, swath, productType))
        for i in range(len(noise)):
          if noise[i].startswith(start):
            inNoiseFile = os.path.join(safeDir, noise[i])
            outNoiseFile = os.path.join(outDir, noise[i])
        subset_noise(inNoiseFile, outNoiseFile, params)

        if polarization == 'DV':
          start = ('./measurement/{0}-{1}-{2}-vh'.format(mission, swath,
            productType))
        elif polarization == 'DH':
          start = ('./measurement/{0}-{1}-{2}-hv'.format(mission, swath,
            productType))
        for i in range(len(measurement)):
          if measurement[i].startswith(start):
            inMeasurementFile = os.path.join(safeDir, measurement[i])
            outMeasurementFile = os.path.join(outDir, measurement[i])
        subset_measurement(inMeasurementFile, outMeasurementFile, params)


      for burst in bursts:
        polygon = burst['polygon']
        ring = polygon.GetGeometryRef(0)
        for i in range(0, ring.GetPointCount()):
          (lon, lat, height) = ring.GetPoint(i)
          if lat < minLat:
            minLatPt = ring.GetPoint(i)
            minLat = lat
          elif lat > maxLat:
            maxLatPt = ring.GetPoint(i)
            maxLat = lat
          elif lon < minLon:
            minLonPt = ring.GetPoint(i)
            minLon = lon
          elif lon > maxLon:
            maxLonPt = ring.GetPoint(i)
            maxLon = lon
    '''

  '''
  corners = ('{0},{1} {2},{3} {4},{5} {6},{7}'.format(minLatPt[1], minLatPt[0],
    minLonPt[1], minLonPt[0], maxLatPt[1], maxLatPt[0], maxLonPt[1],
    maxLonPt[0]))

  # Update preview

  # Write manifest file
  print('Writing manifest file ...')
  inManifestFile = os.path.join(safeDir, 'manifest.safe')
  outManifestFile = os.path.join(outDir, 'manifest.safe')
  subset_manifest(inManifestFile, outManifestFile, times, aoiSwaths, corners)

  # Calculate CRC16 for manifest
  '''



def repack_sentinel(listFile, shapeFile, workDir):

  # Set up environment and get basic metadata out of granule name
  gdal.UseExceptions()
  gdal.PushErrorHandler('CPLQuietErrorHandler')

  # Extract polygon from AOI shapefile
  print('Extracting polygon from AOI shapefile ...')
  aoiMultipolygon, spatialRef = shape2geometry_only(shapeFile)
  if spatialRef.IsGeographic() == 0:
    aoiMultipolygon, spatialRef = geometry_proj2geo(aoiMultipolygon, spatialRef)

  # Read the list of granules
  zipFiles = [line.strip() for line in open(listFile)]
  safeDirs = []
  for zipFile in zipFiles:
    safeDir = subset_granule(os.path.abspath(zipFile), aoiMultipolygon, workDir)
    safeDirs.append(safeDir)

  # Merge granules to one granule
  if len(safeDirs) > 1:
    safeDir = merge_granules(safeDirs, workDir)

  '''
  # Zip the granule
  print('Zipping new granule ...')
  outDir = os.path.abspath(os.path.join(workDir, 'final'))
  os.chdir(outDir)
  zipFile = safeDir.replace('SAFE', 'zip')
  zip = zipfile.ZipFile(zipFile, 'w', zipfile.ZIP_DEFLATED)
  zipPath = os.path.basename(safeDir)
  for root, dirs, files in os.walk(zipPath):
    for file in files:
      zip.write(os.path.join(root, file))
  zip.close()
  '''


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='repack_sentinel',
    description='Repackage Sentinel granules based on a AOI shapefile',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('granule', metavar='<granule>',
    help='list of zipped Sentinel granule files')
  parser.add_argument('shape', metavar='<shapefile>',
    help='name of the AOI shapefile')
  parser.add_argument('work', metavar='<work directory>',
    help='name of the working directory')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  repack_sentinel(args.granule, args.shape, args.work)
