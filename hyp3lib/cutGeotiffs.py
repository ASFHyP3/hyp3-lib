"""Clip a bunch of geotiffs to the same area"""

from __future__ import print_function, absolute_import, division, unicode_literals

from hyp3lib import saa_func_lib as saa
import re
import os
import argparse
import numpy as np
from osgeo import gdal


def get_max_pixel_size(files):
    pix_size = -999
    for fi in files:
        (x1, y1, t1, p1) = saa.read_gdal_file_geo(saa.open_gdal_file(fi))
        tmp = t1[1]
        pix_size = max(pix_size, tmp)

    if pix_size == -999:
        Exception("No valid pixel sizes found")
    return pix_size


def get_corners(fi):
    (x_pix, y_pix, t1, p1) = saa.read_gdal_file_geo(saa.open_gdal_file(fi))
    ullon = t1[0]
    ullat = t1[3]
    lrlon = t1[0] + x_pix * t1[1]
    lrlat = t1[3] + y_pix * t1[5]
    return ullon, ullat, lrlon, lrlat


def get_overlap(coords, fi):
    (x_pix, y_pix, t1, p1) = saa.read_gdal_file_geo(saa.open_gdal_file(fi))

    ullon1 = t1[0]
    ullat1 = t1[3]
    lrlon1 = t1[0] + x_pix * t1[1]
    lrlat1 = t1[3] + y_pix * t1[5]

    ullon2 = coords[0]
    ullat2 = coords[1]
    lrlon2 = coords[2]
    lrlat2 = coords[3]

    ullat = min(ullat1, ullat2)
    ullon = max(ullon1, ullon2)
    lrlat = max(lrlat1, lrlat2)
    lrlon = min(lrlon1, lrlon2)

    return ullon, ullat, lrlon, lrlat


def get_zone_from_proj(fi):
    zone = None
    dst = gdal.Open(fi)
    p1 = dst.GetProjection()
    ptr = p1.find("UTM zone ")
    if ptr != -1:
        (zone, hemi) = [t(s) for t, s in zip((int, str), re.search("(\d+)(.)", p1[ptr:]).groups())]
    return zone


def get_hemisphere(fi):
    hemi = None
    dst = gdal.Open(fi)
    p1 = dst.GetProjection()
    ptr = p1.find("UTM zone ")
    if ptr != -1:
        (zone, hemi) = [t(s) for t, s in zip((int, str), re.search('(\d+)(.)', p1[ptr:]).groups())]
    return hemi


def parse_zones(files):
    zones = []
    for fi in files:
        zone = get_zone_from_proj(fi)
        if zone:
            zones.append(zone)
    return np.asarray(zones, dtype=np.int8)


def cut_files(files):

    if len(files) == 1:
        print("Nothing to do!!!  Exiting...")
        return 0 

    # Find the largest pixel size of all scenes
    pix_size = get_max_pixel_size(files)
    print(f"Maximum pixel size {pix_size}")

    # Get the median UTM zone and hemisphere
    home_zone = np.median(parse_zones(files))
    print(f"Home zone is {home_zone}")
    hemi = get_hemisphere(files[0])
    print(f"Hemisphere is {hemi}")
 
    # Reproject files as needed
    print("Checking projections")
    new_files = []
    for fi in files:
        my_zone = get_zone_from_proj(fi)
        name = fi.replace(".tif", "_reproj.tif")
        if my_zone != home_zone:
            print(f"Reprojecting {fi} to {name}")
            if hemi == "N":
                proj = ('EPSG:326%02d' % int(home_zone))
            else:
                proj = ('EPSG:327%02d' % int(home_zone))
            gdal.Warp(name, fi, dstSRS=proj, xRes=pix_size, yRes=pix_size, targetAlignedPixels=True)
            new_files.append(name)
        else:
            os.symlink(fi,name)   
            new_files.append(name)
            print(f"Linking {fi} to {name}")

    # Find the overlap between all scenes
    coords = get_corners(files[0])
    for x in range(len(files) - 1):
        coords = get_overlap(coords, files[x + 1])
    
    # Check to make sure there was some overlap
    print("Clipping coordinates: {}".format(coords))
    diff1 = (coords[2] - coords[0]) / pix_size
    diff2 = (coords[3] - coords[1]) / pix_size * -1.0
    print("Found overlap size of {}x{}".format(int(diff1), int(diff2)))
    if diff1 < 1 or diff2 < 1:
        print("ERROR:  There was no overlap between scenes")
        exit(1)

    # Finally, clip all scenes to the overlap region at the largest pixel size
    lst = list(coords)
    tmp = lst[3]
    lst[3] = lst[1]
    lst[1] = tmp
    coords = tuple(lst)
    print("Pixsize : x = {} y = {}".format(pix_size, -1 * pix_size))
    for x in range(len(files)):
        file1 = files[x]
        file1_new = file1.replace('.tif', '_clip.tif')
        print("    clipping file {} to create file {}".format(file1, file1_new))
        gdal.Warp(file1_new, file1, outputBounds=coords, xRes=pix_size, yRes=-1 * pix_size,
                  creationOptions = ['COMPRESS=LZW'])


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument(
        "infiles", nargs='+',
        help="Geotiff files to clip; output will be have _clip appended to the file name"
    )
    args = parser.parse_args()

    cut_files(args.infiles)


if __name__ == "__main__":
    main()
