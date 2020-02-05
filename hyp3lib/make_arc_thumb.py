#!/usr/bin/env python
"""Creates an arcgis compatible thumbnail"""

import argparse
from PIL import Image
import base64
import os
import sys


def pngtothumb(pngfile):

    # Modify the png to a jpg thumbnail, then encode to base64
    rgb_im = Image.open(pngfile).convert('RGB')
    x, y = rgb_im.size
    if x>y:
        width = 200
        length = 200 * y/x
    else:
        length = 200
        width = 200 * x/y

    size = length,width
    thumb = rgb_im.thumbnail(size)
    thumbfile = rgb_im.save('tmp_thumb.jpg')
    encoded = base64.b64encode(open(r'tmp_thumb.jpg', "rb").read())
    os.remove("tmp_thumb.jpg")
    return(encoded)


def main():
    """Main entrypoint"""

    # entrypoint name can differ from module name, so don't pass 0-arg
    cli_args = sys.argv[1:] if len(sys.argv) > 1 else None

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('input',help='Name of input PNG file')
    args = parser.parse_args(cli_args)

    pngtothumb(args.input)
  

if __name__ == '__main__':
    main()
