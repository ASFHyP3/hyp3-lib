"""RGB decomposition of a dual-pol RTC

The RGB decomposition enhances RTC dual-pol data for visual interpretation. It
decomposes the co-pol and cross-pol signal into these color channels:
    red: simple bounce (polarized) with some volume scattering
    green: volume (depolarized) scattering
    blue: simple bounce with very low volume scattering

In the case where the volume to simple scattering ratio is larger than expected
for typical vegetation, such as in glaciated areas or some forest types, a teal
color (green + blue) can be used
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Union

import numpy as np
from osgeo import gdal, osr


def rtc2color(copol_tif: Union[str, Path], crosspol_tif: Union[str, Path], threshold: float, out_tif: Union[str, Path],
              cleanup=False, teal=False, amp=False, real=False):
    """RGB decomposition of a dual-pol RTC

    Args:
        copol_tif: The co-pol RTC GeoTIF
        crosspol_tif: The cross-pol RTC GeoTIF
        threshold: Decomposition threshold value in db
        out_tif: The output color GeoTIFF file name
        cleanup: Cleanup artifacts using a -48 db power threshold
        teal: Combine green and blue channels because the volume to simple scattering ratio is high
        amp: input TIFs are in amplitude and not power
        real: Output real (floating point) values instead of RGB scaled (0--255) ints
    """
    # FIXME: Can we just determine if we should use teal?

    # Suppress GDAL warnings but raise python exceptions
    # https://gis.stackexchange.com/a/91393
    gdal.UseExceptions()
    gdal.PushErrorHandler('CPLQuietErrorHandler')

    clean_threshold = pow(10.0, -48.0 / 10.0)  # db to power
    power_threshold = pow(10.0, threshold / 10.0)  # db to power

    # used scale the results to fit inside RGB 1-255 (ints), with 0 for no/bad data
    scale_factor = 1.0 if real else 254.0
    # FIXME: Float32 or 64?
    out_type = gdal.GDT_Float32 if real else gdal.GDT_Byte

    copol = gdal.Open(copol_tif)
    crosspol = gdal.Open(crosspol_tif)

    geotransform = copol.GetGeoTransform()
    proj_wkt = copol.GetProjectionRef()

    cols = min(copol.RasterXSize, crosspol.RasterXSize)
    rows = min(copol.RasterYSize, crosspol.RasterYSize)

    # FIXME: do we really need this?
    # Estimate memory required...
    size = float(rows * cols) / float(1024 * 1024 * 1024)  # in Gibibyte
    # print('float16 variables: cp,xp,diff,zp,rp,bp,red = {} GB'.format(size*14))
    # print('uint8 variables: mask, below_threshold_mask = {} GB".format(size*2))
    logging.warning(f'Data size is {rows} lines by {cols} samples ({size} GiPixels)')
    # FIXME: this is the ram usage for *one* variable, not for this whole script
    logging.warning(f'Estimated Total RAM usage = {size * 16} GiB')

    logging.info(f'Reading co-pol image {copol_tif}')
    cp = np.nan_to_num(copol.GetRasterBand(1).ReadAsArray()[:rows, :cols])
    copol = None  # because gdal is weird

    if amp:
        cp *= cp

    if cleanup:
        cp[cp < clean_threshold] = 0
    else:
        # FIXME: Should this be here or before amp conversion to power? That is,
        #        are the negative amp values, and if so, are they indicative of
        #        bad data? This *was* done before amp conversion before...
        cp[cp < 0] = 0

    # Read cross-pol image
    logging.info(f'Reading cross-pol image {crosspol_tif}')
    xp = np.nan_to_num(crosspol.GetRasterBand(1).ReadAsArray()[:rows, :cols])
    crosspol = None  # because gdal is weird

    if amp:
        xp *= xp

    if cleanup:
        xp[xp < clean_threshold] = 0
    else:
        # FIXME: Should this be here or before amp conversion to power? That is,
        #        are the negative amp values, and if so, are they indicative of
        #        bad data? This *was* done before amp conversion before...
        xp[xp < 0] = 0

    # Find all our no data and bad data pixels
    # NOTE: we're using crosspol here because it will typically have the most bad
    # data and we want the same mask applied to all 3 channels (otherwise, we'll
    # accidentally be changing colors from intended.
    invalid_xp_mask = ~(xp > 0)
    # mask for applying colors
    below_threshold_mask = xp < power_threshold

    driver = gdal.GetDriverByName('GTiff')
    outRaster = driver.Create(out_tif, cols, rows, 3, out_type, ['COMPRESS=LZW'])
    outRaster.SetGeoTransform((geotransform[0], geotransform[1], 0, geotransform[3], 0, geotransform[5]))
    outRasterSRS = osr.SpatialReference()
    outRasterSRS.ImportFromWkt(proj_wkt)
    outRaster.SetProjection(outRasterSRS.ExportToWkt())

    logging.info('Calculating color decomposition components')

    zp = np.arctan(np.sqrt(np.clip(cp - xp, 0, None))) * 2.0 / np.pi
    zp[~below_threshold_mask] = 0

    rp = 2.0 * np.sqrt(np.clip(cp - 3.0 * xp, 0, None))
    rp[below_threshold_mask] = 0

    gp = 3.0 * np.sqrt(xp)
    gp[below_threshold_mask] = 0

    if not teal:
        bp = np.zeros(cp.shape)
    else:
        bp = 2.0 * np.sqrt(np.clip(3.0 * xp - cp, 0, None))
        bp[below_threshold_mask] = 0

    logging.info('Calculate red channel and save in GeoTIFF')
    outBand = outRaster.GetRasterBand(1)
    red = 1.0 + (rp + zp) * scale_factor
    red[invalid_xp_mask] = 0
    outBand.WriteArray(red)
    del red

    logging.info('Calculate green channel and save in GeoTIFF')
    outBand = outRaster.GetRasterBand(2)

    green = 1.0 + (gp + 2.0 * zp) * scale_factor
    green[invalid_xp_mask] = 0
    outBand.WriteArray(green)
    del green

    logging.info('Calculate blue channel and save in GeoTIFF')
    outBand = outRaster.GetRasterBand(3)
    blue = 1.0 + (bp + 5.0 * zp) * scale_factor
    blue[invalid_xp_mask] = 0
    outBand.WriteArray(blue)

    outRaster = None  # because gdal is weird


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('copol', help='the co-pol RTC GeoTIF')
    parser.add_argument('crosspol', help='the cross-pol GeoTIF')
    parser.add_argument('threshold', type=float, help='decomposition threshold value in dB')
    parser.add_argument('geotiff', help='the output color GeoTIFF file name')
    parser.add_argument('-c', '--cleanup', action='store_true', help='cleanup artifacts using a -48 db power threshold')
    parser.add_argument('-t', '--teal', action='store_true',
                        help='combine green and blue channels because the volume to simple scattering ratio is high')
    parser.add_argument('-a', '--amp', action='store_true', help='input is amplitude, not powerscale')
    parser.add_argument('-r', '--real', action='store_true',
                        help='output real (floating point) values instead of RGB scaled (0--255) ints')
    args = parser.parse_args()

    out = logging.StreamHandler(stream=sys.stdout)
    out.addFilter(lambda record: record.levelno <= logging.INFO)
    err = logging.StreamHandler()
    err.setLevel(logging.WARNING)
    logging.basicConfig(format='%(message)s', level=logging.INFO, handlers=(out, err))

    rtc2color(args.copol, args.crosspol, args.threshold, args.geotiff,
              args.cleanup, args.teal, args.amp, args.float)


if __name__ == '__main__':
    main()
