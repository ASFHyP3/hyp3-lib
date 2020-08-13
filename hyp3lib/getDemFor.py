"""Get a DEM file for a given sentinel1 SAFE file"""

import argparse
import logging
import os
import shutil

from osgeo import gdal

from hyp3lib.get_dem import get_dem
from hyp3lib.execute import execute
from hyp3lib.getSubSwath import get_bounding_box_file
from hyp3lib.saa_func_lib import get_utm_proj


def getDemFile(infile, outfile: str, use_opentopo=False, in_utm=True, post=None, dem_name=None):
    lat_max, lat_min, lon_max, lon_min = get_bounding_box_file(infile)

    if use_opentopo:
        demtype = None
        url = f'http://opentopo.sdsc.edu/otr/getdem' \
              f'?demtype=SRTMGL1&west={lon_min}&south={lat_min}&east={lon_max}&north={lat_max}&outputFormat=GTiff'
        execute(f'wget -O {outfile} "{url}"')

        if in_utm:
            proj = get_utm_proj(lon_min, lon_max, lat_min, lat_max)
            tmpdem = 'tmpdem_getDemFile_utm.tif'
            gdal.Warp(tmpdem, outfile, dstSRS=proj, resampleAlg='cubic')
            shutil.move(tmpdem, outfile)
    else:
        dem_type = 'utm' if in_utm else 'latlon'
        demtype = get_dem(
            lon_min, lat_min, lon_max, lat_max, outfile, post=post, dem_name=dem_name, dem_type=dem_type
        )
        if not os.path.isfile(outfile):
            logging.error(f'Unable to find output file {outfile}')

    return outfile, demtype


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument("SAFEfile", help="S1 SAFE file")
    parser.add_argument("outfile", help="Name of output geotiff DEM file")
    parser.add_argument("-o", "--opentopo", action="store_true", help="Use opentopo instead of get_dem")
    parser.add_argument("-l", "--latlon", action="store_false",
                        help="Create DEM in lat,lon space - dangerous option for polar imagery")
    parser.add_argument("-d", "--dem", help="Only use the specified DEM type")
    parser.add_argument("-p", "--post", help="Posting for creating DEM", type=float)
    args = parser.parse_args()

    log_file = f'getDemFor_{os.getpid()}.log'
    logging.basicConfig(filename=log_file, format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.info('Starting run')

    outfile, demtype = getDemFile(args.SAFEfile, args.outfile, use_opentopo=args.opentopo,
                                  in_utm=args.latlon, post=args.post, dem_name=args.dem)
    logging.info(f'Wrote DEM file {outfile}')


if __name__ == '__main__':
    main()
