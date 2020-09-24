"""Copy metadata from one tif to another"""

from __future__ import print_function, absolute_import, division, unicode_literals

import os
import argparse

from hyp3lib.image.tiff import copy_metadata


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
