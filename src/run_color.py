#!/usr/bin/python

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
import zipfile
import shutil
import numpy as np
from rtc2color import rtc2color
from rtc_sentinel import rtc_sentinel_gamma
from resample_geotiff import resample_geotiff


dh = ['hh', 'hv']
dv = ['vv', 'vh']
threshold = {'iw': -23.5, 'ew': -22.5, ('s1','s2','s3','s4','s5','s6'): -22.5}

def process_rtc(rtcDir, outFile):

  os.chdir(rtcDir)
  rtc_sentinel_gamma(outFile, deadFlag=True, gammaFlag=True, loFlag=True,
    matchFlag=True)


def run_color(inFile, thresholdValue):

  # Work out directory names
  if '.zip' in inFile:
    granule = os.path.basename(inFile)[:-4]
  elif '.SAFE' in inFile:
    granule = os.path.basename(inFile)[:-5]
  else:
    raise Exception('Unrecognized format: '+preFile)
  workDir = os.getcwd()
  rtcDir = granule + '_rtc'
  mission = granule[0:3].lower()
  mode = granule[4:6].lower()
  if np.isnan(float(thresholdValue)):
    thresholdValue = threshold[mode]
  polarization = granule[14:16].lower()
  if polarization == 'dh':
    dualPol = dh
  elif polarization == 'dv':
    dualPol = dv
  else:
    raise Exception('Unrecognized polarization: '+polarization)
  year = granule[17:21]

  # Unzip files if required
  if '.zip' in inFile:
    print('Unzipping granule ...')
    zip_ref = zipfile.ZipFile(inFile, 'r')
    zip_ref.extractall(rtcDir)
    zip_ref.close()
  elif '.SAFE' in inFile:
    print('Copying granule ...')
    os.makedirs(rtcDir)
    shutil.copytree(inFile, os.path.join(rtcDir, inFile))
  else:
    raise Exception('Unrecognized format: '+postFile)
  rtcDir = os.path.abspath(rtcDir)

  # Process RTC
  print('Radiometrically terrain correcting granule ...')
  process_rtc(rtcDir, 'rtc')

  # Perform the color decomposition
  print('Performing color decomposition (threshold: {0} dB) ...'.\
    format(thresholdValue))
  fullpol = ('{0}-{1}-rtcm-{2}-rtc.tif'.format(mission, mode, dualPol[0]))
  fullpolFile = os.path.join(rtcDir, 'PRODUCT', fullpol)
  crosspol = ('{0}-{1}-rtcm-{2}-rtc.tif'.format(mission, mode, dualPol[1]))
  crosspolFile = os.path.join(rtcDir, 'PRODUCT', crosspol)
  rtcLog = os.path.join(rtcDir, 'rtc.log')
  lines = [line.rstrip('\n') for line in open(rtcLog)]
  stateVectorType = 'PREDORB'
  for line in lines:
    if 'S1A_OPER_AUX' in line:
      stateVectorType = os.path.basename(line)[13:19]
  fileSequence = ('{0}-{1}-{2}-RGB'.format(granule, stateVectorType,
    abs(float(thresholdValue))))

  # Generate the product directory
  os.chdir(workDir)
  os.makedirs(fileSequence)
  productDir = os.path.abspath(fileSequence)
  geotiff = os.path.join(productDir, fileSequence + '.tif')
  rtc2color(fullpolFile, crosspolFile, thresholdValue, geotiff, teal=False)

  # Generate KMZ file
  print('Generating KMZ file ...')
  os.chdir(productDir)
  kmzFile = fileSequence + '.kmz'
  resample_geotiff(os.path.basename(geotiff), 1024, 'KML', kmzFile)

  # Generate browse image
  print('Generating browse image ...')
  browseFile = os.path.join(productDir, fileSequence + '.jpg')
  resample_geotiff(geotiff, 1024, 'JPEG', browseFile)

  # Generate ESA citation
  print('Generating ESA citation ...')
  fp = open(os.path.join(productDir, 'ESA_citation.txt'), 'w')
  fp.write('This product contains modified Copernicus Sentinel data ({0}),'\
    ' processed by ESA.'.format(year))
  fp.close()

  # Generate zip file
  print('Generating product zip file (%s.zip) ...' % productDir)
  path, base = os.path.split(productDir)
  shutil.make_archive(productDir, 'zip', path, base)


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='run_color',
    description='Run the color decomposition within Hyp3',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('granule', help='name of the dual-pol granule (input)')
  parser.add_argument('-threshold', default=np.nan,
    help='threshold value in dB (input)')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  run_color(args.granule, args.threshold)
