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
        return(0)

    file1 = files[0]
   
    # Open file1, get projection and pixsize
    dst1 = gdal.Open(file1)
    p1 = dst1.GetProjection()

    # Find the largest pixel size of all scenes
    pix_size = get_max_pixel_size(files)
    print(f"Maximum pixel size {pix_size}")

    # Make sure that UTM projections match
    ptr = p1.find("UTM zone ")
    if ptr != -1:
        (zone1,hemi) = [t(s) for t,s in zip((int,str), re.search("(\d+)(.)",p1[ptr:]).groups())]
        for x in range(len(files)-1):
            file2 = files[x+1]

            # Open up file2, get projection 
            dst2 = gdal.Open(file2)
            p2 = dst2.GetProjection()

            # Cut the UTM zone out of projection2 
            ptr = p2.find("UTM zone ")
            zone2 = re.search("(\d+)",p2[ptr:]).groups()
            zone2 = int(zone2[0])

            if zone1 != zone2:
                print("Projections don't match... Reprojecting %s" % file2)
                if hemi == "N":
                    proj = ('EPSG:326%02d' % int(zone1))
                else:
                    proj = ('EPSG:327%02d' % int(zone1))
                print("    reprojecting post image")
                print("    proj is %s" % proj)
                name = file2.replace(".tif","_reproj.tif")
                gdal.Warp(name,file2,dstSRS=proj,xRes=pix_size,yRes=pix_size)
                files[x+1] = name

    # Find the overlap between all scenes
    coords = get_corners(files[0])
    for x in range (len(files)-1):
        coords = get_overlap(coords,files[x+1])
    
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
    print("Pixsize : x = {} y = {}".format(pix_size,-1*pix_size))
    for x in range (len(files)):
        file1 = files[x]
        file1_new = file1.replace('.tif','_clip.tif')
        print("    clipping file {} to create file {}".format(file1, file1_new))
        #        dst_d1 = gdal.Translate(file1_new,file1,projWin=coords,xRes=pix_size,yRes=pix_size,creationOptions = ['COMPRESS=LZW'])
        gdal.Warp(file1_new,file1,outputBounds=coords,xRes=pix_size,yRes=-1*pix_size,creationOptions = ['COMPRESS=LZW'])


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
