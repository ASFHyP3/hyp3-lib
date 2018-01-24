#!/usr/bin/python

import argparse
from argparse import RawTextHelpFormatter
import sys
import os
import lxml.etree as et
from execute import execute
from PIL import Image


def phase_color_image(inFile, outFile):

  xmlFile = inFile + '.xml'
  parser = et.XMLParser(remove_blank_text=True)
  doc = et.parse(xmlFile, parser)
  width = int(doc.xpath('/imageFile/component[@name="coordinate1"]/property' \
    '[@name="size"]/value')[0].text)

  # Use MDX to generate amplitude image in ppm
  cmd = ('mdx {0} -s {1} -amp -r4 -rtlr {2} -P'.format(inFile, width, width*4))
  execute(cmd)
  os.rename('out.ppm', 'amp.ppm')

  # Use MDX to generate phase image in ppm
  cmd = ('mdx {0} -s {1} -CW -unw -r4 -rhdr {2} -cmap cmy ' \
    '-wrap 6.283185307179586 -P'.format(inFile, width, width*4))
  execute(cmd)
  os.rename('out.ppm', 'phase.ppm')

  # Read phase and apply amp as mask
  amp = Image.open('amp.ppm').convert('L')
  phase = Image.open('phase.ppm').convert('RGBA')
  mask = amp.point(lambda i: i < 1 and 255)
  phase.paste(mask, None, mask)
  img = phase.getdata()
  out = []
  for pixel in img:
    if pixel[0] == 255 and pixel[1] == 255 and pixel[2] == 255:
      out.append((255, 255, 255, 0))
    else:
      out.append(pixel)
  phase.putdata(out)
  phase.save(outFile)

  # Clean up
  os.remove('amp.ppm')
  os.remove('phase.ppm')


if __name__ == '__main__':

  parser = argparse.ArgumentParser(prog='phase_color_image',
    description='Generating an ISCE unwrapped phase color image (color only)',
    formatter_class=RawTextHelpFormatter)
  parser.add_argument('input', metavar='<input>',
    help='name of unwrapped phase color image in ISCE format')
  parser.add_argument('output', metavar='<output>',
    help='name of unwrapped phase color image in PNG format')
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  args = parser.parse_args()

  phase_color_image(args.input, args.output)
