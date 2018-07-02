#!/usr/bin/python

import shutil
import os, sys
from osgeo import gdal
import argparse
from argparse import RawTextHelpFormatter

def make_cog(inFile,outFile):

    tmpFile = 'cog_{}.tif'.format(os.getpid())
    shutil.copy(inFile,tmpFile)
    os.system('gdaladdo -r average {} 2 4 8 16'.format(tmpFile))

    co = ["TILED=YES","COMPRESS=DEFLATE","COPY_SRC_OVERVIEWS=YES"]
    gdal.Translate(outFile,tmpFile,creationOptions=co,noData="0")

#    os.system('gdal_translate {} {}  -a_nodata 0 -co TILED=YES -co COMPRESS=DEFLATE -co COPY_SRC_OVERVIEWS=YES'.format(tmpFile,outFile))
    os.remove(tmpFile)

if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='make_cog',
    description='Creates a Cloud Optimized Geotiff from the input geotiff(s)',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('geotiff',nargs='+',help='name of GeoTIFF file (input)')

  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  for myfile in args.geotiff:
      if not os.path.exists(myfile):
        print('ERROR: GeoTIFF file (%s) does not exist!' % myfile)
        sys.exit(1)
      if not os.path.splitext(myfile)[1] == '.tif':
        print('ERRORL Input file (%s) is not geotiff!' % myfile)
        sys.exit(1)

      outfile = myfile.replace(".tif","_cog.tif")
      make_cog(myfile,outfile)

