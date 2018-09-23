#!/usr/bin/env python

###############################################################################
# iscegeo2geotiff
#
# Project:  APD_INSAR 
# Purpose:  Convert ISCE .geo files into geotiffs
#          
# Author:   Tom Logan, Jeremy Nicoll
#
###############################################################################
# Copyright (c) 2017, Alaska Satellite Facility
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
# 
# You should have received a copy of the GNU Library General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
###############################################################################
import sys
import os
import re
import zipfile
import shutil
from lxml import etree
import numpy as np
from osgeo import gdal
from execute import execute

#
# The kmlfile created by mdx.py contains the wrong png file name.
# This won't work.  So, we change the text to be the new name.
#
def fixKmlName(inKML,inName):
    tree = etree.parse(inKML)
    rt = tree.getroot()
    rt[0][0][3][0].text = inName
    of = open(inKML,'wb')
    of.write(b'<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n')
    tree.write(of,pretty_print=True)

def makeKMZ(infile,outfile):
    kmlfile = infile + ".kml"
    kmzfile = outfile + ".kmz"
    pngfile = infile + ".png"
    outpng = outfile + ".png"
    lrgfile = outfile + "_large.png"
    
    # Create the colorized kml file and png image
    cmd = "mdx.py {0} -kml {1}".format(infile,kmlfile)
    execute(cmd)
    
    #fix the name in the kml file!!!
    fixKmlName(kmlfile,lrgfile)

    # scale the PNG image to browse size
    gdal.Translate("temp.png",pngfile,format="PNG",width=0,height=1024)
    gdal.Translate("tmpl.png",pngfile,format="PNG",width=0,height=2048)
    
    shutil.move("temp.png",pngfile)
    shutil.move("tmpl.png",lrgfile)

    # finally, zip the kmz up
    with zipfile.ZipFile(kmzfile,'w') as myzip:
        myzip.write(kmlfile)
        myzip.write(lrgfile)
    shutil.move(pngfile,outpng)


def convert_files(s1aFlag,proj=None,res=30):

    makeKMZ("filt_topophase.unw.geo","colorized_unw")
    makeKMZ("filt_topophase.flat.geo","color")

    if proj is None:
        gdal.Translate("phase.tif","filt_topophase.unw.geo",bandList=[1],creationOptions = ['COMPRESS=PACKBITS'])
    else:
        gdal.Translate("tmp.tif","filt_topophase.unw.geo",bandList=[1],creationOptions = ['COMPRESS=PACKBITS'])
        gdal.Warp("phase.tif","tmp.tif",dstSRS=proj,xRes=res,yRes=res,resampleAlg="cubic",dstNodata=0,creationOptions = ['COMPRESS=LZW'])
        os.remove("tmp.tif")

    # Create browse aux.xml files
    gdal.Translate("phase.png","phase.tif",format="PNG",height=1024)
    shutil.move("phase.png.aux.xml","colorized_unw.png.aux.xml")
    shutil.copy("colorized_unw.png.aux.xml","color.png.aux.xml")
    
    # Create large browse aux.xml files
    gdal.Translate("phase_large.png","phase.tif",format="PNG",height=2048)
    shutil.move("phase_large.png.aux.xml","colorized_unw_large.png.aux.xml")
    shutil.copy("colorized_unw_large.png.aux.xml","color_large.png.aux.xml")

    if proj is None:
        gdal.Translate("amp.tif","filt_topophase.unw.geo",bandList=[2],creationOptions = ['COMPRESS=PACKBITS'])
    else:
        gdal.Translate("tmp.tif","filt_topophase.unw.geo",bandList=[2],creationOptions = ['COMPRESS=PACKBITS'])
        gdal.Warp("amp.tif","tmp.tif",dstSRS=proj,xRes=res,yRes=res,resampleAlg="cubic",dstNodata=0,creationOptions = ['COMPRESS=LZW'])
        os.remove("tmp.tif")
    
    # Create the coherence image
    if proj is None:
        gdal.Translate("coherence.tif","phsig.cor.geo",creationOptions = ['COMPRESS=PACKBITS'])
    else:
        gdal.Translate("tmp.tif","phsig.cor.geo",creationOptions = ['COMPRESS=PACKBITS'])
        gdal.Warp("coherence.tif","tmp.tif",dstSRS=proj,xRes=res,yRes=res,resampleAlg="cubic",dstNodata=0,creationOptions = ['COMPRESS=LZW'])
        os.remove("tmp.tif")

def main():
  convert_files(True)

if __name__ == "__main__":
  main()

