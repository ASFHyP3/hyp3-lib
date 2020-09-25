"""Create a water body mask wherein all water is 0 and land is 1"""

import argparse
import logging
import os
from tempfile import NamedTemporaryFile

from osgeo import gdal, ogr


def get_water_mask(upper_left, lower_right, res, gcs=True, mask_value=1):
    mask_location = '/vsicurl/https://asf-dem-east.s3.amazonaws.com/WATER_MASK'

    xmin, ymax = upper_left
    xmax, ymin = lower_right

    if gcs:
        shpfile = f'{mask_location}/GSHHG/GSHHS_f_L1.shp'
        src_ds = ogr.Open(shpfile)
        src_lyr = src_ds.GetLayer()

        logging.info("Using xmin, xmax {} {}, ymin, ymax {} {}".format(xmin, xmax, ymin, ymax))

        ncols = int((xmax - xmin) / res + 0.5)
        nrows = int((ymax - ymin) / res + 0.5)

        logging.info("Creating water body mask of size {} x {} (lxs) using {}".format(nrows, ncols, shpfile))

        geotransform = (xmin, res, 0, ymax, 0, -res)
        dst_ds = gdal.GetDriverByName('MEM').Create('', ncols, nrows, 1, gdal.GDT_Byte)
        dst_rb = dst_ds.GetRasterBand(1)
        dst_rb.Fill(0)
        dst_rb.SetNoDataValue(0)
        dst_ds.SetGeoTransform(geotransform)

        _ = gdal.RasterizeLayer(dst_ds, [mask_value], src_lyr)
        dst_ds.FlushCache()
        mask = dst_ds.GetRasterBand(1).ReadAsArray()
        del dst_ds

    else:
        if ymin > 0:
            mask_file = f'{mask_location}/Antimeridian_UTM1N_WaterMask1.tif'
        else:
            mask_file = f'{mask_location}/Antimeridian_UTM1S_WaterMask1.tif'

        coords = [xmin, ymax, xmax, ymin]
        with NamedTemporaryFile() as tmpfile:
            gdal.Translate(tmpfile.name, mask_file, projWin=coords, xRes=res, yRes=res)
            srs_ds = gdal.Open(tmpfile.name)
            mask = srs_ds.GetRasterBand(1).ReadAsArray()
            del srs_ds

    return mask


def apply_wb_mask(tiffile, outfile, maskval=0, gcs=True, band=1):
    """
    Given a tiffile input, create outfile, filling in all water areas with the
    maskval.
    """

    logging.info(f"Using mask value of {maskval}")
    tif_info = gdal.Info(tiffile, format='json')
    upper_left = tif_info['cornerCoordinates']['upperLeft']
    lower_right = tif_info['cornerCoordinates']['lowerRight']

    src_ds = gdal.Open(tiffile)
    data = src_ds.GetRasterBand(band).ReadAsArray()
    proj = src_ds.GetProjection()
    trans = src_ds.GetGeoTransform()
    del src_ds

    logging.info("Applying water body mask")
    mask = get_water_mask(upper_left, lower_right, trans[1], gcs=gcs)
    data[mask == 0] = maskval

    dst_ds = gdal.GetDriverByName('GTiff').Create(
        outfile, data.shape[1], data.shape[0], band, gdal.GDT_Float32
    )
    dst_ds.SetProjection(proj)
    dst_ds.SetGeoTransform(trans)
    dst_ds.GetRasterBand(1).WriteArray(data)
    dst_ds.GetRasterBand(1).SetNoDataValue(maskval)
    del dst_ds


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('tiffile', help='Name of tif file to mask')
    parser.add_argument('outfile', help='Name of output masked file')
    parser.add_argument('-m', '--maskval', help='Mask value to apply; default 0', type=float, default=0)
    args = parser.parse_args()

    log_file = "apply_wb_mask_{}_log.txt".format(os.getpid())
    logging.basicConfig(filename=log_file, format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.info("Starting run")

    apply_wb_mask(args.tiffile, args.outfile, maskval=args.maskval)


if __name__ == '__main__':
    main()
