"""Extend the coverage next to the dateline"""

from __future__ import print_function, absolute_import, division, unicode_literals

import argparse
import os
from osgeo import ogr


def extendDateline(inFile, outFile, degrees):

  driver = ogr.GetDriverByName("ESRI Shapefile")
  if os.path.exists(outFile):
    driver.DeleteDataSource(outFile)
  inData = driver.Open(inFile, 0)
  outData = driver.CreateDataSource(outFile)
  inLayer = inData.GetLayer()
  spatialRef = inLayer.GetSpatialRef()
  outLayer = outData.CreateLayer('', geom_type=ogr.wkbPolygon,
    srs=spatialRef)
  featureDefinition = outLayer.GetLayerDefn()
  fieldDefinition = ogr.FieldDefn('tile', ogr.OFTString)
  fieldDefinition.SetWidth(100)
  outLayer.CreateField(fieldDefinition)
  for inFeature in inLayer:
    inPolygon = inFeature.GetGeometryRef()
    outRing = ogr.Geometry(ogr.wkbLinearRing)
    outExtraRing = ogr.Geometry(ogr.wkbLinearRing)
    extra = False
    for inRing in inPolygon:
      numPoints = inRing.GetPointCount()
      for ii in range(numPoints):
        point = inRing.GetPoint(ii)
        minLon = -179.999 + degrees
        if point[0] <= minLon:
          extra = True
        outRing.AddPoint_2D(point[0], point[1])
        outExtraRing.AddPoint_2D(point[0]+360.0, point[1])
    tile = inFeature.GetField('tile')
    outPolygon = ogr.Geometry(ogr.wkbPolygon)
    outPolygon.AddGeometry(outRing)
    outFeature = ogr.Feature(featureDefinition)
    outFeature.SetField('tile', tile)
    outFeature.SetGeometry(outPolygon)
    outLayer.CreateFeature(outFeature)
    outFeature = None
    if extra == True:
      outPolygon = ogr.Geometry(ogr.wkbPolygon)
      outPolygon.AddGeometry(outExtraRing)
      outFeature = ogr.Feature(featureDefinition)
      outFeature.SetField('tile', tile)
      outFeature.SetGeometry(outPolygon)
      outLayer.CreateFeature(outFeature)
      outFeature = None
  outData = None


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('inShape', metavar='<inShapefile>',
                        help='name of the input shapefile')
    parser.add_argument('outShape', metavar='<outShapefile>',
                        help='name of the output shapefile')
    parser.add_argument('degrees', metavar='<degrees>',
                        help='number of degrees to extend dateline')
    args = parser.parse_args()

    extendDateline(args.inShape, args.outShape, float(args.degrees))


if __name__ == '__main__':
    main()
