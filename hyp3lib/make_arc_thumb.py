#!/usr/bin/python

# Generate a thumbnail for inclusion in ArcGIS Item Description metadata
#
# Heidi Kristenson, Tom Logan
# August 2018

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
    thumb = rgb_im.thumbnail(size)
    thumbfile = rgb_im.save('tmp_thumb.jpg')
    encoded = base64.b64encode(open(r'tmp_thumb.jpg', "rb").read())
    os.remove("tmp_thumb.jpg")
    return(encoded)

if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='make_arc_thumb.py',
      description='Creates an arcgis compatible thumbnail')
  parser.add_argument('input',help='Name of input PNG file')
  args = parser.parse_args()
  pngtothumb(args.input)
  

  

  
