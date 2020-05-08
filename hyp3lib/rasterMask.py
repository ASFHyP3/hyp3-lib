"""Generate an AOI mask and apply it"""

from __future__ import print_function, absolute_import, division, unicode_literals

import argparse
import os
import numpy as np
from osgeo import gdal
from hyp3lib.asf_geometry import geotiff2data, data2geotiff
from hyp3lib.asf_time_series import vector_meta


def applyRasterMask(inFile, maskFile, outFile):

  (data, dataGeoTrans, dataProj, dataEPSG, dataDtype, dataNoData) = \
    geotiff2data(inFile)
  (mask, maskGeoTrans, maskProj, maskEPSG, maskDtype, maskNoData) = \
    geotiff2data(maskFile)

  data = data.astype(np.float32)
  mask = mask.astype(np.float32)
  # (dataRows, dataCols) = data.shape
  dataOriginX = dataGeoTrans[0]
  dataOriginY = dataGeoTrans[3]
  # dataPixelSize = dataGeoTrans[1]
  (maskRows, maskCols) = mask.shape
  maskOriginX = maskGeoTrans[0]
  maskOriginY = maskGeoTrans[3]
  maskPixelSize = maskGeoTrans[1]
  offsetX = int(np.rint((maskOriginX - dataOriginX)/maskPixelSize))
  offsetY = int(np.rint((dataOriginY - maskOriginY)/maskPixelSize))
  data = data[offsetY:maskRows+offsetY,offsetX:maskCols+offsetX]
  data *= mask

  data2geotiff(data, dataGeoTrans, dataProj, 'FLOAT', np.nan, outFile)


def rasterMask(inFile, maskFile, aoiFile, maskAoiFile, outFile):

  ### Extract relevant metadata from AOI shapefile
  (fields, proj, extent, features) = vector_meta(aoiFile)
  pixelSize = features[0]['pixSize']
  epsg = features[0]['epsg']
  proj = ('EPSG:{0}'.format(epsg))
  coords = (extent[0], extent[2], extent[1], extent[3])

  ### Generate raster mask
  gdal.Warp(maskAoiFile, maskFile, format='GTiff', dstSRS=proj, xRes=pixelSize,
    yRes=pixelSize, resampleAlg='cubic', outputBounds=coords,
    outputType=gdal.GDT_Byte, creationOptions=['COMPRESS=LZW'])

  ### Apply raster mask to image
  applyRasterMask(inFile, maskAoiFile, outFile)

def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('inFile', help='name of the file to be masked')
    parser.add_argument('maskFile', help='name of the external mask file')
    parser.add_argument('aoiFile', help='name of the AOI polygon file')
    parser.add_argument('maskAoiFile', help='name of the AOI mask file')
    parser.add_argument('outFile', help='name of the masked file')
    args = parser.parse_args()

    rasterMask(
        args.inFile, args.maskFile, args.aoiFile, args.maskAoiFile, args.outFile
    )


if __name__ == '__main__':
    main()
