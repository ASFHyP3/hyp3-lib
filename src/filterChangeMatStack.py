#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
import h5py
from asf_time_series import *


def filterChangeMatStack(inFile, size, iter, outFile):

  ### Read image
  mat = h5py.File(inFile, 'r')
  data = np.asarray(mat['stackSACD'].value)
  (time, cols, rows) = data.shape

  ### Initialize netCDF file
  meta = {}
  meta['institution'] = 'Alaska Satellite Facility'
  meta['title'] = '<TBD>'
  meta['source']  = '<TBD>'
  meta['comment'] = '<TBD>'
  meta['reference'] = '<TBD>'
  meta['cols'] = int(cols)
  meta['rows'] = int(rows)
  meta['refTime'] = '20000101T000000'
  meta['epsg'] = 32601
  meta['imgLongName'] = 'long name'
  meta['imgUnits'] = 'none'
  meta['imgNoData'] = 0
  meta['minX'] = 0
  meta['maxX'] = int(cols)
  meta['minY'] = 0
  meta['maxY'] = int(rows)
  meta['pixelSize'] = 1
  meta['refTime'] = datetime.strptime('20000101T000000', '%Y%m%dT%H%M%S')
  initializeNetcdf(outFile, meta)

  ### Filter settings
  kernelSize = (int(size),int(size))
  iterations = int(iter)
  refTime = datetime.strptime('20000101T000001', '%Y%m%dT%H%M%S')

  ### Morphological filter
  for t in range(time):
    change = filter_change(data[t,:,:], kernelSize, iterations)
    addImage2netcdf(data[t,:,:], outFile, 'image', refTime)


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='filterChangeMatStack',
    description='filters a change detection time series Matlab file using a ' \
      'morphological filter',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('inFile', metavar='<input file>',
    help='name of the unfiltered input file')
  parser.add_argument('-size', metavar='<kernel size>',
    help='size of filter kernel in pixels', default=5)
  parser.add_argument('-iter', metavar='<iterations>',
    help='number of iterations for filtering', default=1)
  parser.add_argument('outFile', metavar='<output file>',
    help='name of the filtered output file')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.inFile):
    print('Matlab file (%s) does not exist!' % args.inFile)
    sys.exit(1)

  filterChangeMatStack(args.inFile, args.size, args.iter, args.outFile)
