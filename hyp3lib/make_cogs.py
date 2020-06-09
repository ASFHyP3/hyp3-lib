"""Creates a Cloud Optimized Geotiff from the input geotiff(s)"""

import argparse
import glob
import logging
import os
import shutil

from osgeo import gdal


def cogify_dir(dir="PRODUCT",debug=False,res=30):
    back = os.getcwd()
    os.chdir(dir)
    tmpfile = "tmp_cog_{}.tif".format(os.getpid())
    for myfile in glob.glob("*.tif"):
        logging.info("Converting file {} into COG".format(myfile))
        make_cog(myfile,tmpfile,res=res)
        shutil.move(tmpfile,myfile)
    os.chdir(back)


def make_cog(inFile,outFile,debug=False,res=30):
    print("Creating COG file {} from input file {}".format(outFile, inFile))
    tmpFile = 'cog_{}.tif'.format(os.getpid())
    shutil.copy(inFile,tmpFile)

    if res == 10:
        os.system('gdaladdo -r average {} 2 4 8 16 32'.format(tmpFile))
    else:
        os.system('gdaladdo -r average {} 2 4 8 16'.format(tmpFile))

    if debug:
        shutil.copy(tmpFile,"make_cog1.tif")

    co = ["TILED=YES","COMPRESS=DEFLATE","COPY_SRC_OVERVIEWS=YES"]
    gdal.Translate(outFile,tmpFile,creationOptions=co,noData="0")

    if debug:
        shutil.copy(outFile,"make_cog2.tif")

    os.remove(tmpFile)


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('geotiff', nargs='+', help='name of GeoTIFF file (input)')

    logFile = "make_cogs_{}.log".format(os.getpid())
    logging.basicConfig(filename=logFile, format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.info("Starting run")

    args = parser.parse_args()

    for myfile in args.geotiff:
        if not os.path.exists(myfile):
            parser.error(f'GeoTIFF file {myfile} does not exist!')
        if not os.path.splitext(myfile)[1] == '.tif':
            parser.error(f'Input file {myfile} is not a GeoTFF!')

        outfile = myfile.replace(".tif", "_cog.tif")
        make_cog(myfile, outfile)


if __name__ == '__main__':
    main()

