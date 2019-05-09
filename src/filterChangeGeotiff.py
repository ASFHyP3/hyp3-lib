#!/usr/bin/python3

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
import h5py
from asf_time_series import *


def filterChangeGeotiff(inFile, size, iter, outFile):

  ### Read input image
  (data, geoTrans, proj, epsg, dtype, noData) = geotiff2data(inFile)

  ### Filter settings
  kernelSize = (int(size),int(size))
  iterations = int(iter)

  ### Morphological filter
  change = filter_change(data, kernelSize, iterations)

  ### Write output image
  data2geotiff(change, geoTrans, proj, dtype, noData, outFile)


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='filterChangeGeotiff',
    description='filters a change detection GeoTIFF file using a ' \
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
    print('GeoTIFF file (%s) does not exist!' % args.inFile)
    sys.exit(1)

  filterChangeGeotiff(args.inFile, args.size, args.iter, args.outFile)
