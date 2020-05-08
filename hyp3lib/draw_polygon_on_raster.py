"""Draws a polygon from a shapefile onto a raster image"""

from __future__ import print_function, absolute_import, division, unicode_literals

import argparse
import shutil
import os

import lxml.etree as et
from imageio import imread
from osgeo import gdal, ogr, osr
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as mplt
import matplotlib.lines as mlines


def write_worldfile(gt, worldFile):

  world = open(worldFile, 'w')
  world.write('%.10f\n' % float(gt[1]))
  world.write('%.10f\n' % float(gt[2]))
  world.write('%.10f\n' % float(gt[4]))
  world.write('%.10f\n' % float(gt[5]))
  world.write('%.10f\n' % (float(gt[0])+float(gt[1])/2.0))
  world.write('%.10f\n' % (float(gt[3])+float(gt[5])/2.0))
  world.close()


def write_aux_file(spatialRef, auxFile):

  aux = et.Element('PAMDataset')
  et.SubElement(aux, 'SRS').text = spatialRef.ExportToWkt()
  meta = et.SubElement(aux, 'Metadata')
  et.SubElement(meta, 'MDI', {'key':'AREA_OR_POINT'}).text = 'Area'
  et.SubElement(meta, 'MDI', {'key':'TIFFTAG_RESOLUTIONUNIT'}).text = \
    '1 (unitless)'
  et.SubElement(meta, 'MDI', {'key':'TIFFTAG_XRESOLUTION'}).text = '1'
  et.SubElement(meta, 'MDI', {'key':'TIFFTAG_YRESOLUTION'}).text = '1'
  band = et.SubElement(aux, 'PAMRasterBand', {'band':'1'})
  et.SubElement(band, 'NoDataValue').text = '0.00000000000000E+00'
  domain = et.SubElement(band, 'Metadata', {'domain':'IMAGE_STRUCTURE'})
  et.SubElement(domain, 'MDI', {'key':'COMPRESSION'}).text = 'JPEG'
  with open(auxFile, 'wb') as outF:
    outF.write(et.tostring(aux, pretty_print=True))


def get_projected_vector_geometry(shapeFile, rasterSpatialRef):

  driver = ogr.GetDriverByName('ESRI Shapefile')
  shape = driver.Open(shapeFile, 0)
  vectorMultipolygon = ogr.Geometry(ogr.wkbMultiPolygon)
  layer = shape.GetLayer()
  vectorSpatialRef = layer.GetSpatialRef()
  if vectorSpatialRef != rasterSpatialRef:
    coordTrans = osr.CoordinateTransformation(vectorSpatialRef, rasterSpatialRef)
  for feature in layer:
    geometry = feature.GetGeometryRef()
    count = geometry.GetGeometryCount()
    if geometry.GetGeometryName() == 'MULTIPOLYGON':
      for i in range(count):
        polygon = geometry.GetGeometryRef(i)
        if vectorSpatialRef != rasterSpatialRef:
          polygon.Transform(coordTrans)
        vectorMultipolygon.AddGeometry(polygon)
    else:
      if vectorSpatialRef != rasterSpatialRef:
        geometry.Transform(coordTrans)
      vectorMultipolygon.AddGeometry(geometry)
  shape.Destroy()

  return vectorMultipolygon


def gcs2poly_geometry(gcsPolygon, rasterSpatialRef):

  vectorMultipolygon = ogr.Geometry(ogr.wkbMultiPolygon)
  vectorSpatialRef = osr.SpatialReference()
  vectorSpatialRef.ImportFromEPSG(4326)
  coordTrans = osr.CoordinateTransformation(vectorSpatialRef, rasterSpatialRef)
  geometry = gcsPolygon.ImportFromWkt()
  count = geometry.GetGeometryCount()
  if geometry.GetGeometryName() == 'MULTIPOLYGON':
    for i in range(count):
      polygon = geometry.GetGeometryRef(i)
      polygon.Transform(coordTrans)
      vectorMultipolygon.AddGeometry(polygon)
  else:
    geometry.Transform(coordTrans)
    vectorMultipolygon.AddGeometry(geometry)

  return vectorMultipolygon


def get_raster_spatial_reference(rasterFile):

  gdal.UseExceptions()
  gdal.PushErrorHandler('CPLQuietErrorHandler')
  inRaster = gdal.Open(rasterFile)
  rasterProj = inRaster.GetProjection()
  rasterSpatialRef = osr.SpatialReference(wkt = rasterProj)

  return rasterSpatialRef


def intersect_raster_with_polygon(rasterFile, vectorPolygon):

  gdal.UseExceptions()
  gdal.PushErrorHandler('CPLQuietErrorHandler')
  inRaster = gdal.Open(rasterFile)
  gt = inRaster.GetGeoTransform()
  originX = gt[0]
  originY = gt[3]
  cols = inRaster.RasterXSize
  rows = inRaster.RasterYSize
  ulX = originX
  ulY = originY
  urX = originX + gt[1]*cols
  urY = originY
  lrX = originX + gt[1]*cols + gt[2]*rows
  lrY = originY + gt[4]*cols + gt[5]*rows
  llX = originX
  llY = originY + gt[4]*cols + gt[5]*rows
  geometry = ('MULTIPOLYGON ((( %f %f, %f %f, %f %f, %f %f, %f %f )))' %
    (ulX, ulY, urX, urY, lrX, lrY, llX, llY, ulX, ulY))
  rasterPolygon = ogr.CreateGeometryFromWkt(geometry)
  intersection = rasterPolygon.Intersection(vectorPolygon)

  return intersection


def proj2pixel(x, y, inverse_geo_transform):

  px, py = gdal.ApplyGeoTransform(inverse_geo_transform, x, y)
  px = int(px) - 1
  py = int(py) - 1

  return (px, abs(py))


def draw_polygon_on_raster(inRasterFile, polygon, color, outRasterFile):

  # Extract information from raster image
  gdal.UseExceptions()
  gdal.PushErrorHandler('CPLQuietErrorHandler')
  inRaster = gdal.Open(inRasterFile)
  fileFormat = inRaster.GetDriver().LongName
  rasterProj = inRaster.GetProjection()
  rasterSpatialRef = osr.SpatialReference(wkt = rasterProj)
  cols = inRaster.RasterXSize
  rows = inRaster.RasterYSize
  geo_transform = inRaster.GetGeoTransform()
  inverse_geo_transform = gdal.InvGeoTransform(geo_transform)
  line = []
  sample = []
  for k in range(0, polygon.GetGeometryCount()):
    geometry = polygon.GetGeometryRef(k)
    for i in range(0, geometry.GetPointCount()):
      point = geometry.GetPoint(i)
      (px, py) = proj2pixel(point[0], point[1], inverse_geo_transform)
      line.append(py)
      sample.append(px)

  # Draw polygon
  figRows = float(rows)/100.0
  figCols = float(cols)/100.0
  fig = mplt.figure(figsize=(figCols, figRows), dpi=100, frameon=False)
  image = imread(inRasterFile)
  mplt.imshow(image, interpolation='none')
  mplt.axis('off')
  mplt.subplots_adjust(left=0, bottom=0, right=1, top=1, hspace=0, wspace=0)
  sub = mplt.subplot(111)
  polyline = mlines.Line2D(sample, line, linewidth=2.0, color=color)
  sub.add_line(polyline)
  with open(outRasterFile, 'w') as outfile:
    fig.canvas.print_jpg(outfile)

  # Create extra GEO files
  if fileFormat == 'JPEG JFIF':
    write_worldfile(geo_transform, outRasterFile.replace('.jpg', '.wld'))
    write_aux_file(rasterSpatialRef, outRasterFile + '.aux.xml')


def draw_polygon_from_shape_on_raster(inRaster, shapeFile, polyColor, outRaster):

  # Assign colors
  color = {}
  color['blue'] = 'b'
  color['green'] = 'g'
  color['red'] = 'r'
  color['cyan'] = 'c'
  color['magenta'] = 'm'
  color['yellow'] = 'y'
  color['black'] = 'k'
  color['white'] = 'w'

  # Extracting intersection of raster image and shapefile geometry
  rasterSpatialRef = get_raster_spatial_reference(inRaster)
  vectorPolygon = get_projected_vector_geometry(shapeFile, rasterSpatialRef)
  polygon = intersect_raster_with_polygon(inRaster, vectorPolygon)

  # Draw polygon on geocoded image
  if polygon:
    draw_polygon_on_raster(inRaster, polygon, color[polyColor], outRaster)
  else:
    shutil.copy(inRaster,outRaster)

def draw_polygon_from_gcs_polygon_on_raster(inRaster, gcsPolygon, polyColor,
  outRaster):

  # Assign colors
  color = {}
  color['blue'] = 'b'
  color['green'] = 'g'
  color['red'] = 'r'
  color['cyan'] = 'c'
  color['magenta'] = 'm'
  color['yellow'] = 'y'
  color['black'] = 'k'
  color['white'] = 'w'

  # Extracting intersection of raster image and shapefile geometry
  rasterSpatialRef = get_raster_spatial_reference(inRaster)
  vectorPolygon = gcs2poly_geometry(gcsPolygon, rasterSpatialRef)
  polygon = intersect_raster_with_polygon(inRaster, vectorPolygon)

  # Draw polygon on geocoded image
  draw_polygon_on_raster(inRaster, polygon, color[polyColor], outRaster)


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('inRaster', help='name of the input raster file')
    parser.add_argument('shape', help='name of the polygon shapefile to be drawn')
    parser.add_argument('color', help='color of the polygon')
    parser.add_argument('outRaster', help='name of the output raster file')
    args = parser.parse_args()

    draw_polygon_from_shape_on_raster(
        args.inRaster, args.shape, args.color, args.outRaster
    )


if __name__ == '__main__':
    main()
