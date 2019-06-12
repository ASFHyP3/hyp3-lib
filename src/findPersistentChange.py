#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
from asf_time_series import *


def findPersistentChange(inFile, outFile):

  ### Set parameters
  consecutiveImages = 5
  persistentThreshold = 4

  ### Read SACD results
  sacdResults = [line.rstrip('\n') for line in open(inFile)]
  time = len(sacdResults)
  (proj, gt, shape, pixel) = raster_meta(sacdResults[0])
  (rows, cols) = shape

  ### Set up change arrays
  negChange = np.zeros((time, rows, cols), dtype=np.uint8)
  posChange = np.zeros((time, rows, cols), dtype=np.uint8)
  runChange = np.zeros((rows, cols), dtype=np.uint8)
  persistentChange = np.zeros((rows, cols), dtype=np.uint8)

  ### Load SACD results
  for ii in range(time):
    filename = os.path.splitext(os.path.basename(sacdResults[ii]))[0]
    print('Loading {0} ...'.format(filename))
    (data, geoTrans, proj, epsg, dtype, noData) = geotiff2data(sacdResults[ii])
    negChange[ii,:,:][data==1] = 1
    posChange[ii,:,:][data==3] = 1

  ### Determine persistent change
  print('Determining persistent change ...')
  for ii in range(time-consecutiveImages):
    runChange = np.sum(negChange[ii:ii+consecutiveImages,:,:], axis=0)
    persistentChange[runChange>=persistentThreshold] = 1
    runChange = np.sum(posChange[ii:ii+consecutiveImages,:,:], axis=0)
    persistentChange[runChange>=persistentThreshold] = 1

  ### Save persistent change to file
  print('Saving persistent change to file ({0})'.format(outFile))
  data2geotiff(persistentChange, geoTrans, proj, 'BYTE', 0, outFile)


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='findPersistentChange',
    description='generates an area of interest mask shapefile',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('inFile', metavar='<SACD results>',
    help='name of the list file containing SACD results')
  parser.add_argument('outFile', metavar='<persistent change file>',
    help='name of the persistent change file')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.inFile):
    print('SACD results list file (%s) does not exist!' % args.inFile)
    sys.exit(1)

  findPersistentChange(args.inFile, args.outFile)
