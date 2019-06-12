#!/usr/bin/python

import argparse
from argparse import RawTextHelpFormatter
import os
import sys
import xlsxwriter
from osgeo import gdal, ogr, osr
from asf_time_series import *
from asf_geometry import *
import netCDF4 as nc
import yaml

tolerance = 0.05
noiseFloor = 0.001


def geotiff2time_series(listFile, tsEPSG, maskFile, xlsxFile, latlon, aoiFile,
  tiled, ncFile, yamlFile, outDir):

  ### Work through GeoTIFF file list and generate a time series mask
  files = [line.rstrip('\n') for line in open(listFile)]
  numGranules = len(files)

  ### Determine the EPSG code (if none is given as input)
  if tsEPSG == 0:
    epsg = []
    for ii in range(numGranules):
      (proj, gt, shape, pixel) = raster_meta(files[ii])
      if proj.GetAttrValue('AUTHORITY', 0) == 'EPSG':
        epsg.append(int(proj.GetAttrValue('AUTHORITY', 1)))
    tsEPSG = int(np.median(epsg))
    epsg = None

  ### Determine pixel size
  (proj, gt, shape, pixel) = raster_meta(files[0])
  posting = gt[1]

  ### Extract metadata into lists
  granule = []
  originX = []
  originY = []
  lrX = []
  lrY = []
  pixelSize = []
  epsg = []
  pixel_area = []
  rows = []
  cols = []
  for ii in range(numGranules):
    inFile = os.path.basename(files[ii])
    print('Extracting metadata from {0} ...'.format(inFile))
    granule.append(inFile.replace('.tif', ''))
    (proj, gt, shape, pixel) = raster_meta(files[ii])
    if proj.GetAttrValue('AUTHORITY', 0) == 'EPSG':
      epsg.append(int(proj.GetAttrValue('AUTHORITY', 1)))
    if tsEPSG != epsg[ii]:
      minX = gt[0]
      maxY = gt[3]
      maxX = minX + posting*shape[1]
      minY = maxY - posting*shape[0]
      corners = ogr.Geometry(ogr.wkbMultiPoint)
      ul = ogr.Geometry(ogr.wkbPoint)
      ul.AddPoint(minX, maxY)
      corners.AddGeometry(ul)
      ll = ogr.Geometry(ogr.wkbPoint)
      ll.AddPoint(minX, minY)
      corners.AddGeometry(ll)
      ur = ogr.Geometry(ogr.wkbPoint)
      ur.AddPoint(maxX, maxY)
      corners.AddGeometry(ur)
      lr = ogr.Geometry(ogr.wkbPoint)
      lr.AddPoint(maxX, minY)
      corners.AddGeometry(lr)
      corners = reproject_corners(corners, posting, epsg[ii], tsEPSG)
      for point in corners:
        (x, y, z) = point.GetPoint(0)
        gt = (x, posting, 0.0, y, 0.0, -posting)
        break;
    originX.append(gt[0])
    originY.append(gt[3])
    pixelSize.append(gt[1])
    rows.append(shape[0])
    cols.append(shape[1])
    pixel_area.append(pixel)
    lrX.append(gt[0]+gt[1]*shape[1])
    lrY.append(gt[3]+gt[5]*shape[0])

  if aoiFile != None:

    ### Get area of interest from shapefile
    ## Determine EPSG
    (fields, proj, extent, features) = vector_meta(aoiFile)
    if proj.GetAttrValue('AUTHORITY', 0) == 'EPSG':
      dataEPSG = int(proj.GetAttrValue('AUTHORITY', 1))

    ## Re-project AOI shapefile (if needed) and determine extent
    ogrDriver = ogr.GetDriverByName('ESRI Shapefile')
    if dataEPSG != tsEPSG:
      inVector = ogrDriver.Open(aoiFile)
      inLayer = inVector.GetLayer()
      inProj = inLayer.GetSpatialRef()
      outProj = osr.SpatialReference()
      outProj.ImportFromEPSG(tsEPSG)
      transform = osr.CoordinateTransformation(inProj, outProj)
      memDriver = ogr.GetDriverByName('MEMORY')
      inShape = memDriver.CreateDataSource('mem')
      outLayer = inShape.CreateLayer('', outProj, ogr.wkbPolygon)
      outLayer.CreateField(ogr.FieldDefn('id', ogr.OFTInteger))
      ii = 0
      for inFeature in inLayer:
        reprojected = inFeature.GetGeometryRef()
        reprojected.Transform(transform)
        geometry = ogr.CreateGeometryFromWkb(reprojected.ExportToWkb())
        definition = outLayer.GetLayerDefn()
        outFeature = ogr.Feature(definition)
        outFeature.SetField('id', ii)
        outFeature.SetGeometry(geometry)
        outLayer.CreateFeature(outFeature)
        ii += 1
        outFeature = None
      (aoiMinX, aoiMaxX, aoiMinY, aoiMaxY) = outLayer.GetExtent()
    else:
      inShape = ogrDriver.Open(aoiFile)
      outLayer = inShape.GetLayer()
      outProj = outLayer.GetSpatialRef()
      (aoiMinX, aoiMaxX, aoiMinY, aoiMaxY) = outLayer.GetExtent()
    aoiLines = int(np.rint((aoiMaxY - aoiMinY)/posting))
    aoiSamples = int(np.rint((aoiMaxX - aoiMinX)/posting))
    maskGT = (aoiMinX, posting, 0, aoiMaxY, 0, -posting)

    ## Rasterize AOI polygon
    gdalDriver = gdal.GetDriverByName('MEM')
    outRaster = gdalDriver.Create('', aoiSamples, aoiLines, 1, gdal.GDT_Float32)
    outRaster.SetGeoTransform((aoiMinX, posting, 0, aoiMaxY, 0, -posting))
    outRaster.SetProjection(outProj.ExportToWkt())
    outBand = outRaster.GetRasterBand(1)
    outBand.SetNoDataValue(0)
    outBand.FlushCache()
    gdal.RasterizeLayer(outRaster, [1], outLayer, burn_values=[1])
    mask = outRaster.GetRasterBand(1).ReadAsArray()
    inShape = None
    outRaster = None

  elif latlon != None:

    ### Determine mask based on lat/lon boundary box
    ## Reprojct latitude extent to UTM coordinates
    (minX, maxX, minY, maxY) = np.float64(latlon)

    ## Add points to multiPoint
    corners = ogr.Geometry(ogr.wkbMultiPoint)
    ul = ogr.Geometry(ogr.wkbPoint)
    ul.AddPoint(minX, maxY)
    corners.AddGeometry(ul)
    ll = ogr.Geometry(ogr.wkbPoint)
    ll.AddPoint(minX, minY)
    corners.AddGeometry(ll)
    ur = ogr.Geometry(ogr.wkbPoint)
    ur.AddPoint(maxX, maxY)
    corners.AddGeometry(ur)
    lr = ogr.Geometry(ogr.wkbPoint)
    lr.AddPoint(maxX, minY)
    corners.AddGeometry(lr)

    ## Re-project corner coordinates
    corners = reproject_corners(corners, posting, 4326, tsEPSG)
    (aoiMinX, aoiMaxX, aoiMinY, aoiMaxY) = corners.GetEnvelope()
    aoiLines = int(np.rint((aoiMaxY - aoiMinY)/posting))
    aoiSamples = int(np.rint((aoiMaxX - aoiMinX)/posting))

    ## Generate mask
    mask = np.ones((aoiSamples, aoiLines), dtype=np.float32)
    maskGT = (aoiMinX, posting, 0, aoiMaxY, 0, -posting)

  else:

    ### Look for common overlap of all GeoTIFF images
    ## Determine maximum extent
    samples = int(np.rint((max(lrX) - min(originX))/np.median(pixelSize)))
    lines = int(np.rint((max(originY) - min(lrY))/np.median(pixelSize)))
    ulX = min(originX)
    ulY = max(originY)
    pixSize = np.median(pixelSize)
    maskMaxGT = (ulX, pixSize, 0, ulY, 0, -pixSize)

    ## Extract raster boundary masks
    offsetX = []
    offsetY = []
    files = [line.rstrip('\n') for line in open(listFile)]
    for ii in range(numGranules):
      inFile = os.path.basename(files[ii])
      print('Creating boundary mask ({0}) ...'.format(inFile))
      (mask, colFirst, rowFirst, gt, proj) = \
        geotiff2boundary_mask(files[ii], tsEPSG, None)
      (maskRows, maskCols) = mask.shape
      maskOriginX = gt[0]
      maskOriginY = gt[3]
      offX = int(np.rint((maskOriginX - ulX)/pixSize))
      offY = int(np.rint((ulY - maskOriginY)/pixSize))
      offsetX.append(colFirst)
      offsetY.append(rowFirst)
      dataMask = np.zeros((lines, samples), dtype=np.float32)
      dataMask[offY:maskRows+offY,offX:maskCols+offX] = mask
      if ii == 0:
        maskMax = dataMask
      else:
        maskMax *= dataMask
      dataMask = None

    ## Cut blackfill
    print('Cutting blackfill ...')
    (mask, colFirst, rowFirst, maskGT) = cut_blackfill(maskMax, maskMaxGT)
    maskMax = None

  ### Save mask (if requested)
  if maskFile != None:
    print('Saving mask file ({0}) ...'.format(os.path.basename(maskFile)))
    data2geotiff(mask, maskGT, proj, 'BYTE', 0, maskFile)

  ### Write metadata to Excel spreadsheet (if requested)
  if xlsxFile != None:
    outFile = os.path.basename(xlsxFile)
    print('Writing information to Excel spreadsheet file (%s) ...' % outFile)
    workbook = xlsxwriter.Workbook(xlsxFile)
    worksheet = workbook.add_worksheet('metadata')
    bold = workbook.add_format({'bold':True})
    worksheet.write('A1', 'Granule', bold)
    worksheet.write('B1', 'OriginX', bold)
    worksheet.write('C1', 'OriginY', bold)
    worksheet.write('D1', 'Pixel size', bold)
    worksheet.write('E1', 'EPSG', bold)
    worksheet.write('F1', 'Pixel/Area', bold)
    worksheet.write('G1', 'Rows', bold)
    worksheet.write('H1', 'Columns', bold)
    worksheet.write('I1', 'LowerRightX', bold)
    worksheet.write('J1', 'LowerRightY', bold)
    worksheet.write('K1', 'OffsetX', bold)
    worksheet.write('L1', 'OffsetY', bold)
    for ii in range(numGranules):
      worksheet.write(ii+1, 0, granule[ii])
      worksheet.write(ii+1, 1, float(originX[ii]))
      worksheet.write(ii+1, 2, float(originY[ii]))
      worksheet.write(ii+1, 3, float(pixelSize[ii]))
      worksheet.write(ii+1, 4, int(epsg[ii]))
      worksheet.write(ii+1, 5, pixel_area[ii])
      worksheet.write(ii+1, 6, int(rows[ii]))
      worksheet.write(ii+1, 7, int(cols[ii]))
      worksheet.write(ii+1, 8, float(lrX[ii]))
      worksheet.write(ii+1, 9, float(lrY[ii]))
      worksheet.write(ii+1, 10, float(offsetX[ii]))
      worksheet.write(ii+1, 11, float(offsetY[ii]))
    workbook.close()

  ### Extract time stamps from RTC products
  timestamp = []
  for ii in range(numGranules):
    timestamp.append(datetime.strptime(granule[ii][12:27], '%Y%m%dT%H%M%S'))
  timeIndex = np.argsort(timestamp)

  if netcdfFile != None:

    ### Generate nedCDF time series file
    print('Generate netCDF time series file(s) ...')

    if tiled == True:
      (rows, cols) = mask.shape
      tileX = int(float(cols)/1024)
      tileY = int(float(rows)/1024)
      width = int(float(cols)/tileX)
      height = int(float(rows)/tileY)
      restX = cols - tileX*width
      restY = rows - tileY*height

    ## Read auxiliary information from YAML file into a dictionary
    stream = open(yamlFile)
    yamlData = yaml.load(stream)
    stream.close()

    ## Initialize netCDF file
    if tiled == True:
      for kk in range(tileY):
        for ii in range(tileX):

          tileStr = (' (tile {0} {1})'.format(ii+1,kk+1))
          originX = maskGT[0] + (ii+1)*width
          originY = maskGT[3] - (kk+1)*height

          meta = {}
          meta['institution'] = yamlData['global']['institution']
          meta['title'] = yamlData['global']['title'] + tileStr
          meta['source'] = yamlData['global']['source']
          meta['comment'] = yamlData['global']['comment']
          meta['reference'] = yamlData['global']['reference']
          meta['imgLongName'] = yamlData['data']['longName']
          meta['imgUnits'] = yamlData['data']['units']
          meta['imgNoData'] = float(yamlData['data']['noData'])
          meta['epsg'] = tsEPSG
          meta['minX'] = originX
          meta['maxY'] = originY
          meta['maxX'] = originX + posting*width
          meta['cols'] = width
          meta['minY'] = originY - posting*height
          meta['rows'] = height
          meta['pixelSize'] = np.median(pixelSize)
          meta['refTime'] = min(timestamp)

          tileFile = ('%s_tile_%02d_%02d.nc' % (os.path.splitext(ncFile)[0],
            ii+1, kk+1))
          initializeNetcdf(tileFile, meta)

    else:

      meta = {}
      meta['institution'] = yamlData['global']['institution']
      meta['title'] = yamlData['global']['title']
      meta['source'] = yamlData['global']['source']
      meta['comment'] = yamlData['global']['comment']
      meta['reference'] = yamlData['global']['reference']
      meta['imgLongName'] = yamlData['data']['longName']
      meta['imgUnits'] = yamlData['data']['units']
      meta['imgNoData'] = float(yamlData['data']['noData'])
      meta['epsg'] = tsEPSG
      meta['minX'] = maskGT[0]
      meta['maxX'] = maskGT[0] + maskGT[1]*mask.shape[1]
      meta['minY'] = maskGT[3] + maskGT[5]*mask.shape[0]
      meta['maxY'] = maskGT[3]
      meta['cols'] = mask.shape[1]
      meta['rows'] = mask.shape[0]

      initializeNetcdf(ncFile, meta)

  if netcdfFile != None or outDir != None:

    ### Apply mask to images
    files = [line.rstrip('\n') for line in open(listFile)]
    for ii in range(numGranules):
      kk = timeIndex[ii]
      inFile = os.path.basename(files[kk])
      print('Applying mask to image ({0}) ...'.format(inFile))
      inRaster = gdal.Open(files[kk])
      if epsg[kk] != tsEPSG:
        print('Reprojecting ...')
        inRaster = reproject2grid(inRaster, tsEPSG)
      dataGT = inRaster.GetGeoTransform()
      data = inRaster.GetRasterBand(1).ReadAsArray()
      data[data<noiseFloor] = noiseFloor
      data = apply_mask(data, dataGT, mask, maskGT)
      if netcdfFile != None:
        if tiled == True:
          for mm in range(tileY):
            for ll in range(tileX):
              tileFile = ('%s_tile_%02d_%02d.nc' % (os.path.splitext(ncFile)[0],
                ll+1, mm+1))
              beginX = ll*width
              beginY = mm*height
              endX = beginX + width
              endY = beginY + height
              #print('Adding layer to {0} ...'.format(tileFile))
              addImage2netcdf(data[beginY:endY,beginX:endX], tileFile,
                granule[kk], timestamp[kk])
        else:
          addImage2netcdf(data, ncFile, granule[kk], timestamp[kk])
      elif outDir != None:
        if aoiFile != None:
          outFile = os.path.join(os.path.abspath(outDir),
            inFile.replace('.tif','_aoi.tif'))
        else:
          outFile = os.path.join(os.path.abspath(outDir),
            inFile.replace('.tif','_overlap.tif'))
        data2geotiff(data, maskGT, proj, 'FLOAT', np.nan, outFile)
      data = None


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='geotiff2time_series',
    description='generate a time series stack from GeoTIFFs',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('input', metavar='<list file>',
    help='name of the list file of GeoTIFFs')
  parser.add_argument('-epsg', metavar='<code>', action='store',
    default=0, help='EPSG code for the entire time series')
  parser.add_argument('-mask', metavar='<file>', action='store',
    default=None,
    help='name of the mask file (common overlap for the entire stack)')
  parser.add_argument('-excel', metavar='<Excel file>', action='store',
    default=None, help='name of the Excel spreadsheet file')
  aoi = parser.add_mutually_exclusive_group(required=False)
  aoi.add_argument('-latlon', metavar=('<minLon>','<maxLon>','<minLat>',
    '<maxLat>'), action='store', nargs=4, default=None,
    help='bounding box: minLon, maxLon, minLat, maxLat')
  aoi.add_argument('-aoi', metavar='<shapefile>', action='store',
    default=None, help='area of interest shapefile')
  aoi.add_argument('-tile', action='store_true', default=None,
    help='tile the time series (netCDF stack files only)')
  stack = parser.add_mutually_exclusive_group(required=True)
  stack.add_argument('-stack', action='store', nargs=2, default=None,
    metavar=('<netCDF file>','<YAML metadata file>'), help='name of the ' \
    'netCDF time series file and the YAML boilerplate metadata file')
  stack.add_argument('-geotiff', metavar='<output directory>', action='store',
    default=None, help='name of output directory for GeoTIFF files')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  if not os.path.exists(args.input):
    print('GeoTIFF list file (%s) does not exist!' % args.input)
    sys.exit(1)

  netcdfFile = None
  yamlFile = None
  if args.stack != None:
    (netcdfFile, yamlFile) = args.stack

  geotiff2time_series(args.input, int(args.epsg), args.mask, args.excel,
    args.latlon, args.aoi, args.tile, netcdfFile, yamlFile, args.geotiff)
