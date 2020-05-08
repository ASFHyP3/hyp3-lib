# NOTE: This script has a couple of weirdnesses to it.  It calls externally to gdal_translate
#       to convert the DSM and image data to Int16 and Byte, respectively.  This allows for the use
#       of larger images.  It will do this conversion regardless of input type of the original data.
#
#       Large matrices are deleted after they are no longer used.  Not sure if this is more efficient than
#       the usual garbage collector, but have not seen any issues.

from __future__ import print_function, absolute_import, division, unicode_literals

import math

import numpy as np
from osgeo import gdal


def open_gdal_file(filename):
    handle = gdal.Open(filename)
    return handle


def gdal_num_bands(filehandle):
    return filehandle.RasterCount


def read_gdal_metadata(filehandle):
    md = filehandle.GetMetadata()
    return md


def read_gdal_file(filehandle, band=1, gcps=False):
    geotransform = filehandle.GetGeoTransform()
    geoproj = filehandle.GetProjection()
    banddata = filehandle.GetRasterBand(band)
    # type = gdal.GetDataTypeName(banddata.DataType).lower()
    min = banddata.GetMinimum()
    max = banddata.GetMaximum()
    if min is None or max is None:
        (min, max) = banddata.ComputeRasterMinMax(1)
    data = banddata.ReadAsArray()
    if gcps == False:
        return filehandle.RasterXSize, filehandle.RasterYSize, geotransform, geoproj, data
    else:
        gcp = filehandle.GetGCPs()
        gcpproj = filehandle.GetGCPProjection()
        return filehandle.RasterXSize, filehandle.RasterYSize, geotransform, geoproj, gcp, gcpproj, data


def read_gdal_file_small(filehandle, band, xsize, ysize):
    banddata = filehandle.GetRasterBand(band)
    data = banddata.ReadAsArray(0, 0, filehandle.RasterXSize, filehandle.RasterYSize, xsize, ysize)

    return data


def read_gdal_file_subset(filehandle, band, xsize, ysize, xoff=0, yoff=0):
    banddata = filehandle.GetRasterBand(band)
    data = banddata.ReadAsArray(xoff, yoff, xoff + xsize, yoff + ysize, xsize, ysize)
    return data


def read_gdal_file_generic(filehandle, band, xsize, ysize):
    banddata = filehandle.GetRasterBand(band)
    data = banddata.ReadAsArray(0, 0, xsize, ysize, xsize, ysize)

    return data


def read_gdal_file_byscanline(filehandle, xsize, ysize, xoff, yoff, band=1):
    banddata = filehandle.GetRasterBand(band)
    data = banddata.ReadAsArray(xoff, yoff, xsize, ysize, xsize, ysize)
    return data


def read_gdal_file_geo(filehandle, band=1):
    geotransform = filehandle.GetGeoTransform()
    geoproj = filehandle.GetProjection()
    return filehandle.RasterXSize, filehandle.RasterYSize, geotransform, geoproj


def getCorners(fi):
    (x1, y1, t1, p1) = read_gdal_file_geo(open_gdal_file(fi))
    ullon1 = t1[0]
    ullat1 = t1[3]
    lrlon1 = t1[0] + x1 * t1[1]
    lrlat1 = t1[3] + y1 * t1[5]
    return (ullon1, lrlon1, lrlat1, ullat1)


def getPixSize(fi):
    (x1, y1, t1, p1) = read_gdal_file_geo(open_gdal_file(fi))
    return (t1[1])


# Get the UTM zone
def get_zone(lon_min, lon_max):
    center_lon = (lon_min + lon_max) / 2
    zf = (center_lon + 180) / 6 + 1
    zone = math.floor(zf)
    return zone


def get_utm_proj(lon_min, lon_max, lat_min, lat_max):
    zone = get_zone(lon_min, lon_max)
    if (lat_min + lat_max) / 2 > 0:
        proj = ('EPSG:326%02d' % int(zone))
    else:
        proj = ('EPSG:327%02d' % int(zone))
    print("Found proj {}".format(proj))
    return proj


# Reproject a GCS file into UTM coordinates
def reproject_gcs_to_utm(infile, outfile, pixSize):
    lon_min, lon_max, lat_min, lat_max = getCorners(infile)
    proj = get_utm_proj(lon_min, lon_max, lat_min, lat_max)
    print("Using pixel size {}".format(pixSize))
    print("Translating {} to make {}".format(infile, outfile))
    gdal.Warp(outfile, infile, dstSRS=proj, xRes=pixSize, yRes=pixSize, creationOptions=['COMPRESS=LZW'])


# Subroutine for generating All corners
def get_corners(originx, originy, xsize, ysize, xres, yres):
    ulx = originx
    uly = originy
    urx = originx + xsize * xres
    ury = originy
    llx = originx
    lly = originy + ysize * yres
    lrx = originx + xsize * xres
    lry = originy + ysize * yres
    return ulx, uly, urx, ury, llx, lly, lrx, lry


def open_gdal_file_forscanline(file, x, y, trans, proj, dt='UInt16'):
    format = "GTiff"
    driver = gdal.GetDriverByName(format)
    if dt == 'UInt16':
        dst_datatype = gdal.GDT_UInt16
    elif dt == 'Float32':
        dst_datatype = gdal.GDT_Float32
    # dst_ds = driver.Create(file,x,y,1,dst_datatype,["COMPRESS=LZW"])
    dst_ds = driver.Create(file, x, y, 8, dst_datatype, [])
    dst_ds.SetGeoTransform(trans)
    dst_ds.SetProjection(proj)

    return dst_ds


def write_gdal_file_byscanline(driver, xoff, yoff, data, band=1):
    driver.GetRasterBand(band).WriteArray(data, xoff, yoff)


def write_gdal_file(filename, geotransform, geoproj, data, gcps='', gcpproj=''):
    (x, y) = data.shape
    format = "GTiff"
    driver = gdal.GetDriverByName(format)
    dst_datatype = gdal.GDT_Int16
    dst_ds = driver.Create(filename, y, x, 1, dst_datatype)
    northing = geotransform[0]
    weres = geotransform[1]
    rotation = geotransform[2]
    easting = geotransform[3]
    rotation = geotransform[4]
    nsres = geotransform[5]

    dst_ds.GetRasterBand(1).WriteArray(data)
    dst_ds.SetGeoTransform([northing, weres, rotation, easting, rotation, nsres])
    dst_ds.SetProjection(geoproj)
    if gcps != '' and gcpproj != '':
        dst_ds.SetGCPs(gcps, gcpproj)

    return 1


def write_gdal_file_float(filename, geotransform, geoproj, data, nodata=None):
    (x, y) = data.shape
    format = "GTiff"
    driver = gdal.GetDriverByName(format)
    dst_datatype = gdal.GDT_Float32
    dst_ds = driver.Create(filename, y, x, 1, dst_datatype)
    northing = geotransform[0]
    weres = geotransform[1]
    rotation = geotransform[2]
    easting = geotransform[3]
    rotation = geotransform[4]
    nsres = geotransform[5]

    dst_ds.GetRasterBand(1).WriteArray(data)
    if nodata is not None:
        dst_ds.GetRasterBand(1).SetNoDataValue(nodata)
    # dst_ds.SetGeoTransform(geotransform)
    dst_ds.SetGeoTransform([northing, weres, rotation, easting, rotation, nsres])
    dst_ds.SetProjection(geoproj)
    return 1


def write_gdal_file_byte(filename, geotransform, geoproj, data, nodata=None):
    (x, y) = data.shape
    format = "GTiff"
    driver = gdal.GetDriverByName(format)
    dst_datatype = gdal.GDT_Byte
    dst_ds = driver.Create(filename, y, x, 1, dst_datatype)
    geotransform = [item for item in geotransform]
    dst_ds.SetGeoTransform(geotransform)
    dst_ds.GetRasterBand(1).WriteArray(data)
    if nodata is not None:
        dst_ds.GetRasterBand(1).SetNoDataValue(nodata)
    dst_ds.SetProjection(geoproj)

    return 1


def write_gdal_file_rgb(filename, geotransform, geoproj, b1, b2, b3, metadata=None):
    options = []
    (x, y) = b1.shape
    format = "GTiff"
    driver = gdal.GetDriverByName(format)
    dst_datatype = gdal.GDT_Byte
    dst_ds = driver.Create(filename, y, x, 3, dst_datatype, options)
    dst_ds.SetGeoTransform(geotransform)
    dst_ds.SetProjection(geoproj)
    if metadata is not None:
        dst_ds.SetMetadata(metadata)
    dst_ds.GetRasterBand(1).WriteArray(b1)
    dst_ds.GetRasterBand(2).WriteArray(b2)
    dst_ds.GetRasterBand(3).WriteArray(b3)

    return 1


def write_gdal_file_rgba(filename, geotransform, geoproj, b1, b2, b3, b4):
    options = []
    (x, y) = b1.shape
    format = "GTiff"
    driver = gdal.GetDriverByName(format)
    dst_datatype = gdal.GDT_Byte
    dst_ds = driver.Create(filename, y, x, 4, dst_datatype, options)
    dst_ds.SetGeoTransform(geotransform)
    dst_ds.SetProjection(geoproj)
    dst_ds.GetRasterBand(1).WriteArray(b1)
    dst_ds.GetRasterBand(2).WriteArray(b2)
    dst_ds.GetRasterBand(3).WriteArray(b3)
    dst_ds.GetRasterBand(4).WriteArray(b4)

    return 1


def boxcar_y(image, bsize):
    (y, x) = image.shape
    # outimage = np.zeros([y,x],dtype=float32)
    outimage = image
    w = np.ones(bsize)
    # edge = int((bsize - 1) / 2)
    for i in range(0, y):
        gdal.TermProgress_nocb(float(i) / float(y))
        outimage[i, :] = np.convolve(w / w.sum(), image[i, :], mode='same')
    print('100')
    return outimage


def boxcar_x(image, bsize):
    (y, x) = image.shape
    # outimage = np.zeros([y,x],dtype=float32)
    outimage = image
    w = np.ones(bsize)
    # edge = int((bsize - 1) / 2)
    for j in range(0, x):
        gdal.TermProgress_nocb(float(j) / float(x))
        outimage[:, j] = np.convolve(w / w.sum(), image[:, j], mode='same')
    print('100')
    return outimage


def lee(image):
    return 1


def convertToLogPolar():
    return 1


def calcTranslation(master, slave):
    fft1 = np.fft.fft2(master)
    fft2 = np.fft.fft2(slave)
    fft2_conj = np.conjugate(fft2)

    result = fft1 * fft2_conj / abs(fft1 * fft2_conj)
    shift = np.fft.ifft2(result)

    realshift = abs(shift)
    shiftmax = realshift.max()
    # shiftmin = realshift.min()
    shiftmean = realshift.mean()
    shiftsnr = shiftmax / shiftmean

    maxloc = np.argmax(realshift)
    dims = realshift.shape
    maxindex = np.unravel_index(maxloc, dims)
    xloc = maxindex[0]
    yloc = maxindex[1]
    snr = shiftsnr

    return xloc, yloc, snr, shiftmax
