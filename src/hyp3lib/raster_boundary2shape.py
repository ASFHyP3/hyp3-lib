"""generates boundary shapefile from GeoTIFF file"""

import argparse
import os

from scipy import ndimage

from hyp3lib.asf_geometry import geotiff2boundary_mask, data_geometry2shape
from hyp3lib.asf_time_series import raster_metadata


def raster_boundary2shape(inFile, threshold, outShapeFile, use_closing=True, fill_holes = False,
                          pixel_shift=False):
    # Extract raster image metadata
    print('Extracting raster information ...')
    (fields, values, spatialRef) = raster_metadata(inFile)

    print("Initial origin {x},{y}".format(x=values[0]['originX'],y=values[0]['originY']))

    if spatialRef.GetAttrValue('AUTHORITY', 0) == 'EPSG':
        epsg = int(spatialRef.GetAttrValue('AUTHORITY', 1))
    # Generate GeoTIFF boundary geometry
    print('Extracting boundary geometry ...')
    (data, colFirst, rowFirst, geoTrans, proj) = \
        geotiff2boundary_mask(inFile, epsg, threshold,use_closing=use_closing)
    (rows, cols) = data.shape

    print("After geotiff2boundary_mask origin {x},{y}".format(x=geoTrans[0],y=geoTrans[3]))
 
    if fill_holes:
      data = ndimage.binary_fill_holes(data).astype(bool)

#    if pixel_shift:
      if values[0]['pixel']:
          minx = geoTrans[0]
          maxy = geoTrans[3]
          # maxx = geoTrans[0] + cols*geoTrans[1]
          # miny = geoTrans[3] + rows*geoTrans[5]

          # compute the pixel-aligned bounding box (larger than the feature's bbox)
          left = minx -  (geoTrans[1]/2)
          top = maxy - (geoTrans[5]/2)

          values[0]['originX'] = left
          values[0]['originY'] = top 

    print("After pixel_shift origin {x},{y}".format(x=values[0]['originX'],y=values[0]['originY']))

    values[0]['rows'] = rows
    values[0]['cols'] = cols

    # Write broundary to shapefile
    print('Writing boundary to shapefile ...')
    data_geometry2shape(data, fields, values, spatialRef, geoTrans, outShapeFile)


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('input', metavar='<geotiff file>',
             help='name of the GeoTIFF file')
    parser.add_argument('-threshold', metavar='<code>', action='store',
             default=None, help='threshold value what is considered blackfill')
    parser.add_argument('shape', metavar='<shape file>',help='name of the shapefile')

    parser.add_argument('--fill_holes', default=False, action="store_true", help='Turn on hole filling')

    parser.add_argument('--pixel_shift', default=False,
            action="store_true", help='apply pixel shift')

    parser.add_argument('--no_closing',
             default=True,action='store_false',
             help='Switch to turn off closing operation')

    args = parser.parse_args()

    if not os.path.exists(args.input):
        parser.error(f'GeoTIFF file {args.input} does not exist!')

    raster_boundary2shape(
        args.input, args.threshold, args.shape, args.no_closing, args.fill_holes, args.pixel_shift
    )


if __name__ == '__main__':
    main()
