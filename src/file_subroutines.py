import os, re
from execute import execute
import zipfile

#
#  Given a CSV file, download granules and unzip them,
#  removing zip files as we go.  Note, this will unzip
#  and REMOVE ALL ZIP FILES in the current directory.
#
def prepare_files(csvFile):

    cmd = "get_asf.py %s" % csvFile
    execute(cmd)
    os.rmdir("download")
    for myfile in os.listdir("."):
        if ".zip" in myfile:
            zip_ref = zipfile.ZipFile(myfile, 'r')
            zip_ref.extractall(".")
            zip_ref.close()    
            os.remove(myfile)

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
	
    print 'Found %s files to process' % i
    files.sort(key = lambda row: row[1])
    print files

    for i in range(len(files)): 
        filenames.append(files[i][0])
        filedates.append(files[i][1])

    return(filenames,filedates)
