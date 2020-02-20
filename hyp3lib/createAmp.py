#!/usr/bin/env python
"""Convert Geotiff Power to Amplitude"""

from __future__ import print_function, absolute_import, division, unicode_literals

from hyp3lib import saa_func_lib as saa
import numpy as np
import argparse
import os
import sys


def createAmp(fi,nodata=None):
    (x,y,trans,proj,data) = saa.read_gdal_file(saa.open_gdal_file(fi))
    ampdata = np.sqrt(data)
    outfile = fi.replace('.tif','_amp.tif')
    saa.write_gdal_file_float(outfile,trans,proj,ampdata,nodata=nodata)
    return outfile


def main():
    """Main entrypoint"""

    # entrypoint name can differ from module name, so don't pass 0-arg
    cli_args = sys.argv[1:] if len(sys.argv) > 1 else None

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument("infile", nargs="+", help="Input tif filename(s)")
    parser.add_argument("-n", "--nodata", type=float, help="Set nodata value")
    args = parser.parse_args(cli_args)

    infiles = args.infile
    for fi in infiles:
        createAmp(fi, args.nodata)


if __name__ == "__main__":
    main()
