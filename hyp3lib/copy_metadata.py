"""Copy metadata from one tif to another"""

from __future__ import print_function, absolute_import, division, unicode_literals

import os
import argparse
from hyp3lib import saa_func_lib as saa
from osgeo import gdal


def copy_metadata(infile, outfile):
    ds = saa.open_gdal_file(infile)
    md = ds.GetMetadata()
    print(md)

    # ds = saa.open_gdal_file(outfile)
    # ds.SetMetadata(md)

    # outfile2 = "tmp_outfile.tif"
    # gdal.Translate(outfile2,outfile, metadataOptions = md)
    # shutil.move(outfile2,outfile)

    ds = saa.open_gdal_file(outfile)
    for item in md:
        ds1 = gdal.Translate('',ds,format='MEM',metadataOptions = ['{}={}'.format(item,md[item])])
        ds = ds1
    gdal.Translate(outfile,ds1)
 

def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument("infile", help="Input tif filename")
    parser.add_argument("outfile", help="Output tif filename")
    args = parser.parse_args()

    copy_metadata(args.infile, args.outfile)


if __name__ == "__main__":
    main()
