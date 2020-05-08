from __future__ import print_function, absolute_import, division, unicode_literals

import errno
import glob
import os
import re
import zipfile

from hyp3lib.execute import execute


def prepare_files(csv_file):
    """Download granules and unzip granules

    Given a CSV file of granule names, download the granules and unzip them,
    removing the zip files as we go. Note: This will unzip and REMOVE ALL ZIP
    FILES in the current directory.
    """
    cmd = "get_asf.py %s" % csv_file
    execute(cmd)
    os.rmdir("download")
    for myfile in os.listdir("."):
        if ".zip" in myfile:
            try:
                zip_ref = zipfile.ZipFile(myfile, 'r')
                zip_ref.extractall(".")
                zip_ref.close()
            except:
                print("Unable to unzip file {}".format(myfile))
        else:
            print("WARNING: {} not recognized as a zip file".format(myfile))


def get_file_list():
    """
    Return a list of file names and file dates, including all SAFE
    directories, found in the current directory, sorted by date.
    """
    files = []
    filenames = []
    filedates = []

    # Set up the list of files to process
    i = 0
    for myfile in os.listdir("."):
        if ".SAFE" in myfile and os.path.isdir(myfile):
            t = re.split('_+', myfile)
            m = [myfile, t[4][0:15]]
            files.append(m)
            i += 1

    print('Found %s files to process' % i)
    files.sort(key=lambda row: row[1])
    print(files)

    for i in range(len(files)): 
        filenames.append(files[i][0])
        filedates.append(files[i][1])

    return filenames, filedates


def get_dem_tile_list():

    tile_list = None
    for myfile in glob.glob("DEM/*.tif"):
        tile = os.path.basename(myfile)
        if tile_list:
            tile_list = tile_list + ", " + tile
        else:
            tile_list = tile

    if tile_list:
        print("Found DEM tile list of {}".format(tile_list))
        return tile_list
    else:
        print("Warning: no DEM tile list created")
        return None


def mkdir_p(path):
    """
    Make parent directories as needed and no error if existing. Works like `mkdir -p`.
    """
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
