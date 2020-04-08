import os, re
from execute import execute
import zipfile
import glob

#
#  Given a CSV file, download granules and unzip them
#
def prepare_files(csvFile):
    cmd = "get_asf.py %s" % csvFile
    execute(cmd)
    os.rmdir("download")
    for myfile in os.listdir("."):
        unzip_file(myfile)

#
# Given a zipfile, unzip it
#
def unzip_file(myfile):
    if ".zip" in myfile:
        try:
            zip_ref = zipfile.ZipFile(myfile, 'r')
            zip_ref.extractall(".")
            zip_ref.close()    
        except:
            print("Unable to unzip file {}".format(myfile))
    else:
        print("WARNING: {} not recognized as a zip file".format(myfile))


#
# Return lists of file names and file dates, sorted by date.
# Includes all SAFE directories found in the current directory.
#
def get_file_list():

    files = []
    filenames = []
    filedates = []

    # Set up the list of files to process
    i = 0
    for myfile in os.listdir("."):
        if ".SAFE" in myfile and os.path.isdir(myfile):
            t = re.split('_+',myfile)
            m = [myfile,t[4][0:15]]
            files.append(m)
            i = i+1

    print('Found %s files to process' % i)
    files.sort(key = lambda row: row[1])
    print(files)

    for i in range(len(files)): 
        filenames.append(files[i][0])
        filedates.append(files[i][1])

    return(filenames,filedates)


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
        return(None)


