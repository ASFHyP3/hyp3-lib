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


def cleanup_threshold(amp=False, cleanup=False) -> float:
    """Determine the appropriate cleanup threshold value to use in amp or power

    Args:
        amp: input TIF is in amplitude and not power
        cleanup: Cleanup artifacts using a -48 db power threshold

    Returns:
        clean_threshold: the cleaning threshold to use in amp or power
    """
    if amp and cleanup:
        clean_threshold = pow(10.0, -24.0 / 10.0)  # db to amp
    elif cleanup:
        clean_threshold = pow(10.0, -48.0 / 10.0)  # db to power
    else:
        clean_threshold = 0.0

    return clean_threshold


def prepare_geotif_data(geotiff_handle: gdal.Dataset, rows: int, cols: int, amp=False, cleanup=False) -> np.ndarray:
    """Load in and clean the GeoTIFF for calculating the color thresholds

    Args:
        geotiff_handle: gdal Dataset for the GeoTIFF to prepare
        rows: number of data rows to read in
        cols: number of data columns to read in
        amp: input TIF is in amplitude and not power
        cleanup: Cleanup artifacts using a -48 db power threshold

    Returns:
        data: A numpy array containing the prepared GeoTIFF data
    """

    data = np.nan_to_num(geotiff_handle.GetRasterBand(1).ReadAsArray()[:rows, :cols])

    threshold = cleanup_threshold(amp, cleanup)
    data[data < threshold] = 0.0

    if amp:  # to power
        data *= data

    return data


def calculate_color_channel(copol_data: np.ndarray, crosspol_data: np.ndarray, threshold: float,
                            scale_factor: float, color: str):
    """Calculate color channel values for the RGB decomposition of copol and crosspol data

    Args:
        copol_data: copol data
        crosspol_data: crosspol data
        threshold: decomposition threshold value in db
        scale_factor: scale data by this factor
        color: the color channel to calculate

    Returns:
        color_channel: color channel data
    """

    power_threshold = pow(10.0, threshold / 10.0)  # db to power
    below_threshold_mask = crosspol_data < power_threshold

    # I don't know what 'zp' is...
    zp = np.arctan(np.sqrt(np.clip(copol_data - crosspol_data, 0, None))) * 2.0 / np.pi
    zp[~below_threshold_mask] = 0

    if color == 'red':
        z_constant = 1.0
        color_term = 2.0 * np.sqrt(np.clip(copol_data - 3.0 * crosspol_data, 0, None))
        color_term[below_threshold_mask] = 0.0

    elif color == 'green':
        z_constant = 2.0
        color_term = 3.0 * np.sqrt(crosspol_data)
        color_term[below_threshold_mask] = 0.0

    elif color == 'blue':
        z_constant = 5.0
        color_term = np.zeros(copol_data.shape)

    elif color == 'teal':
        z_constant = 5.0
        color_term = 2.0 * np.sqrt(np.clip(3.0 * crosspol_data - copol_data, 0, None))

    else:
        raise ValueError(f'Unknown color {color}, pick red, green, blue, or teal')

    # Find all our no data and bad data pixels
    # NOTE: we're using crosspol here because it will typically have the most bad
    # data and we want the same mask applied to all 3 channels (otherwise, we'll
    # accidentally be changing colors from intended)
    invalid_crosspol_mask = ~(crosspol_data > 0)

    color_channel = 1.0 + (color_term + z_constant * zp) * scale_factor
    color_channel[invalid_crosspol_mask] = 0

    return color_channel


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

    # Suppress GDAL warnings but raise python exceptions
    # https://gis.stackexchange.com/a/91393
    gdal.UseExceptions()
    gdal.PushErrorHandler('CPLQuietErrorHandler')

    copol_handle = gdal.Open(copol_tif)
    crosspol_handle = gdal.Open(crosspol_tif)

    rows = min(copol_handle.RasterYSize, crosspol_handle.RasterYSize)
    cols = min(copol_handle.RasterXSize, crosspol_handle.RasterXSize)

    geotransform = copol_handle.GetGeoTransform()
    projection_reference = copol_handle.GetProjectionRef()

    copol_data = prepare_geotif_data(copol_handle, rows, cols, amp=amp, cleanup=cleanup)
    crosspol_data = prepare_geotif_data(crosspol_handle, rows, cols, amp=amp, cleanup=cleanup)

    copol_handle = None  # How to close because gdal is weird
    crosspol_handle = None  # How to close because gdal is weird

    driver = gdal.GetDriverByName('GTiff')
    out_type = gdal.GDT_Float32 if real else gdal.GDT_Byte
    out_raster = driver.Create(out_tif, cols, rows, 3, out_type, ['COMPRESS=LZW'])
    out_raster.SetGeoTransform((geotransform[0], geotransform[1], 0, geotransform[3], 0, geotransform[5]))
    out_raster_srs = osr.SpatialReference()
    out_raster_srs.ImportFromWkt(projection_reference)
    out_raster.SetProjection(out_raster_srs.ExportToWkt())

    logging.info('Calculating color decomposition components')

    # used scale the results to fit inside RGB 1-255 (ints), with 0 for no/bad data
    scale_factor = 1.0 if real else 254.0

    logging.info('Calculate red channel and save in GeoTIFF')
    red = calculate_color_channel(
        copol_data, crosspol_data, threshold=threshold, scale_factor=scale_factor, color='red'
    )
    out_band = out_raster.GetRasterBand(1)
    out_band.WriteArray(red)
    del red

    logging.info('Calculate green channel and save in GeoTIFF')
    green = calculate_color_channel(
        copol_data, crosspol_data, threshold=threshold, scale_factor=scale_factor, color='green'
    )
    out_band = out_raster.GetRasterBand(2)
    out_band.WriteArray(green)
    del green

    logging.info('Calculate blue channel and save in GeoTIFF')
    blue = calculate_color_channel(
        copol_data, crosspol_data, threshold=threshold, scale_factor=scale_factor, color='teal' if teal else 'blue'
    )
    out_band = out_raster.GetRasterBand(3)
    out_band.WriteArray(blue)
    del blue

    out_raster = None  # How to close because gdal is weird


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('copol', help='the co-pol RTC GeoTIF')
    parser.add_argument('crosspol', help='the cross-pol GeoTIF')
    parser.add_argument('threshold', type=float, help='decomposition threshold value in dB')
    parser.add_argument('geotiff', help='the output color GeoTIFF file name')
    parser.add_argument('-c', '-cleanup', '--cleanup', action='store_true',
                        help='cleanup artifacts using a -48 db power threshold')
    parser.add_argument('-t', '-teal', '--teal', action='store_true',
                        help='combine green and blue channels because the volume to simple scattering ratio is high')
    parser.add_argument('-a', '-amp', '--amp', action='store_true', help='input is amplitude, not powerscale')
    parser.add_argument('-r', '-real', '--real', action='store_true',
                        help='output real (floating point) values instead of RGB scaled (0--255) ints')
    args = parser.parse_args()

    out = logging.StreamHandler(stream=sys.stdout)
    out.addFilter(lambda record: record.levelno <= logging.INFO)
    err = logging.StreamHandler()
    err.setLevel(logging.WARNING)
    logging.basicConfig(format='%(message)s', level=logging.INFO, handlers=(out, err))

    rtc2color(args.copol, args.crosspol, args.threshold, args.geotiff,
              args.cleanup, args.teal, args.amp, args.real)


if __name__ == '__main__':
    main()
