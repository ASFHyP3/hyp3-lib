"""Get a DEM file for a given sentinel1 SAFE file"""

from __future__ import print_function, absolute_import, division, unicode_literals

from hyp3lib import get_dem
import os
import argparse
from hyp3lib.getSubSwath import get_bounding_box_file
from hyp3lib.execute import execute
from osgeo import gdal
import shutil
import logging
from hyp3lib.saa_func_lib import get_utm_proj


def getDemFile(infile,outfile,opentopoFlag=None,utmFlag=True,post=None,demName=None):
    lat_max,lat_min,lon_max,lon_min = get_bounding_box_file(infile)
    if opentopoFlag:
        cmd = "wget -O%s \"http://opentopo.sdsc.edu/otr/getdem?demtype=SRTMGL1&west=%s&south=%s&east=%s&north=%s&outputFormat=GTiff\"" % (outfile,lon_min,lat_min,lon_max,lat_max)
        execute(cmd)
        if utmFlag:
            proj = get_utm_proj(lon_min,lon_max,lat_min,lat_max)
            tmpdem = "tmpdem_getDemFile_utm.tif"
            gdal.Warp("%s" %tmpdem,"%s" % outfile,dstSRS=proj,resampleAlg="cubic")
            shutil.move(tmpdem,"%s" % outfile)
    else:
        if utmFlag:
            demtype = get_dem.get_dem(lon_min,lat_min,lon_max,lat_max,outfile,post=post,demName=demName)
            if not os.path.isfile(outfile):
                logging.error("Unable to find output file {}".format(outfile))
        else:
            demtype = get_dem.get_ll_dem(lon_min,lat_min,lon_max,lat_max,outfile,post=post,demName=demName)
            
    return(outfile,demtype)


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument("SAFEfile",help="S1 SAFE file")
    parser.add_argument("outfile",help="Name of output geotiff DEM file")
    parser.add_argument("-o","--opentopo",action="store_true",help="Use opentopo instead of get_dem")
    parser.add_argument("-l","--latlon",action="store_false",
        help="Create DEM in lat,lon space - dangerous option for polar imagery")
    parser.add_argument("-d","--dem",help="Only use the specified DEM type")
    parser.add_argument("-p","--post",help="Posting for creating DEM",type=float)
    args = parser.parse_args()

    logFile = "getDemFor_{}.log".format(os.getpid())
    logging.basicConfig(filename=logFile,format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',level=logging.DEBUG)
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.info("Starting run")

    outfile,demtype = getDemFile(args.SAFEfile,args.outfile,opentopoFlag=args.opentopo,
                                 utmFlag=args.latlon,post=args.post,demName=args.dem)
    logging.info("Wrote DEM file %s" % outfile)


if __name__ == '__main__':
    main()
