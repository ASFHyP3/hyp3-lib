#!/usr/bin/python

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from datetime import datetime
import zipfile
import shutil
import numpy as np
from rtc2color import rtc2color
from rtc2colordiff import rtc2colordiff
from rtc_sentinel import rtc_sentinel_gamma
from resample_geotiff import resample_geotiff


dh = ['hh', 'hv']
dv = ['vv', 'vh']
threshold = {'iw': -23.5, 'ew': -22.5, ('s1','s2','s3','s4','s5','s6'): -22.5}

def process_rtc(rtcDir, outFile):

  os.chdir(rtcDir)
  rtc_sentinel_gamma(outFile, deadFlag=True, gammaFlag=True, loFlag=True,
    matchFlag=True)


def run_colordiff(preFile, postFile, thresholdValue):

  # Work out directory names
  if '.zip' in preFile:
    preGranule = os.path.basename(preFile)[:-4]
    postGranule = os.path.basename(postFile)[:-4]
  elif '.SAFE' in preFile:
    preGranule = os.path.basename(preFile)[:-5]
    postGranule = os.path.basename(postFile)[:-5]
  else:
    raise Exception('Unrecognized format: '+preFile)
  workDir = os.getcwd()
  rtcPreDir = preGranule + '_rtc'
  rtcPostDir = postGranule + '_rtc'
  preMission = preGranule[0:3].lower()
  postMission = postGranule[0:3].lower()
  mode = preGranule[4:6].lower()
  if np.isnan(float(thresholdValue)):
    thresholdValue = threshold[mode]
  polarization = preGranule[14:16].lower()
  if polarization == 'dh':
    dualPol = dh
  elif polarization == 'dv':
    dualPol = dv
  else:
    raise Exception('Unrecognized polarization: '+polarization)
  preDate = preGranule[17:32]
  postDate = postGranule[17:32]
  deltaTime = datetime.strptime(preDate[:8], '%Y%m%d') - \
    datetime.strptime(postDate[:8], '%Y%m%d')
  days = abs(deltaTime.days)
  year = preGranule[17:21]

  # RTC the pre-event granule
  if '.zip' in preFile:
    print('Unzipping pre-post granule ...')
    zip_ref = zipfile.ZipFile(preFile, 'r')
    zip_ref.extractall(rtcPreDir)
    zip_ref.close()
  elif '.SAFE' in preFile:
    print('Copying pre-post granule ...')
    os.makedirs(rtcPreDir)
    shutil.copytree(preFile, os.path.join(rtcPreDir, preFile))
  else:
    raise Exception('Unrecognized format: '+preFile)
  rtcPreDir = os.path.abspath(rtcPreDir)
  print('Radiometrically terrain correcting pre-evant granule ...')
  process_rtc(rtcPreDir, 'rtc')

  # RTC the post-event granule
  os.chdir(workDir)
  if '.zip' in postFile:
    print('Unzipping post-post granule ...')
    zip_ref = zipfile.ZipFile(postFile, 'r')
    zip_ref.extractall(rtcPostDir)
    zip_ref.close()
  elif '.SAFE' in postFile:
    print('Copying post-post granule ...')
    os.makedirs(rtcPostDir)
    shutil.copytree(postFile, os.path.join(rtcPostDir, postFile))
  else:
    raise Exception('Unrecognized format: '+postFile)
  rtcPostDir = os.path.abspath(rtcPostDir)
  print('Radiometrically terrain correcting post-evant granule ...')
  process_rtc(rtcPostDir, 'rtc')

  # Generate RGB difference image
  print('Generating RGB difference image ...')
  fullpol = ('{0}-{1}-rtcm-{2}-rtc.tif'.format(preMission, mode, dualPol[0]))
  preFullpol = os.path.join(rtcPreDir, 'PRODUCT', fullpol)
  crosspol = ('{0}-{1}-rtcm-{2}-rtc.tif'.format(preMission, mode, dualPol[1]))
  preCrosspol = os.path.join(rtcPreDir, 'PRODUCT', crosspol)
  fullpol = ('{0}-{1}-rtcm-{2}-rtc.tif'.format(postMission, mode, dualPol[0]))
  postFullpol = os.path.join(rtcPostDir, 'PRODUCT', fullpol)
  crosspol = ('{0}-{1}-rtcm-{2}-rtc.tif'.format(postMission, mode, dualPol[1]))
  postCrosspol = os.path.join(rtcPostDir, 'PRODUCT', crosspol)
  rtcLog = os.path.join(rtcPreDir, 'rtc.log')
  lines = [line.rstrip('\n') for line in open(rtcLog)]
  stateVectorType = 'PREDORB'
  for line in lines:
    if 'S1A_OPER_AUX' in line:
      stateVectorType = os.path.basename(line)[13:19]
  fileSequence = ('{0}{1}-{2}-{3}-{4}-{5}-{6}d-RGB-diff'.\
    format(preMission.upper(), postMission[2].upper(), preDate, postDate,
    polarization.upper(), stateVectorType, days))

  os.chdir(workDir)
  os.makedirs(fileSequence)
  productDir = os.path.abspath(fileSequence)
  geotiff = os.path.join(productDir, fileSequence + '.tif')
  rtc2colordiff(preFullpol, preCrosspol, postFullpol, postCrosspol,
    thresholdValue, geotiff, True, False)

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

  parser = argparse.ArgumentParser(prog='run_colordiff',
    description='Run the color difference image within Hyp3',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('pre',
    help='name of the pre-event dual-pol granule (input)')
  parser.add_argument('post',
    help='name of the post-event dual-pol granule (input)')
  parser.add_argument('-threshold', default=np.nan,
    help='threshold value in dB (input)')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  run_colordiff(args.pre, args.post, args.threshold)
