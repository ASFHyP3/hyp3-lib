"""Creates an arcgis compatible thumbnail"""

from __future__ import print_function, absolute_import, division, unicode_literals

import argparse
from PIL import Image
import base64
import os


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
    _ = rgb_im.thumbnail(size)
    _ = rgb_im.save('tmp_thumb.jpg')
    encoded = base64.b64encode(open(r'tmp_thumb.jpg', "rb").read())
    os.remove("tmp_thumb.jpg")
    return(encoded)


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('input',help='Name of input PNG file')
    args = parser.parse_args()

    pngtothumb(args.input)
  

if __name__ == '__main__':
    main()
