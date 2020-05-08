"""Convert ISCE outputs into geotiff, browse, and kmz files"""

from __future__ import print_function, absolute_import, division, unicode_literals

import os
import zipfile
import shutil
from lxml import etree
from osgeo import gdal
from hyp3lib.execute import execute
import argparse


def fixKmlName(inKML,inName):
    """
    The kmlfile created by mdx.py contains the wrong png file name.
    This won't work.  So, we change the text to be the new name.
    """
    tree = etree.parse(inKML)
    rt = tree.getroot()
    rt[0][0][3][0].text = inName
    with open(inKML, 'wb') as of:
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


def create_browse(oldname,pngname,auxname,gcsname,proj,height):
        """Create a browse image"""
        # Use the gcsfile's aux.xml information
        gdal.Translate(pngname,gcsname,format="PNG",height=height)
        shutil.move(auxname,"gcs.aux.xml")

        # Use the GMT5SAR provided PNG file
        gdal.Translate(pngname,oldname,format="PNG",height=height)
        shutil.move("gcs.aux.xml",auxname)

        # Repoject the PNG file into UTM coordinates
        gdal.Warp("tmp.vrt",pngname,format="vrt",dstSRS=proj,resampleAlg="cubic",dstNodata=0)
        gdal.Translate(pngname,"tmp.vrt",format="PNG")
        os.remove("tmp.vrt")


def convert_files(s1aFlag,proj=None,res=30):

    makeKMZ("filt_topophase.unw.geo","unw")
    shutil.move("unw.kmz","colorized_unw.kmz")
    makeKMZ("filt_topophase.flat.geo","col")
    shutil.move("col.kmz","color.kmz")

    gcsname = "tmp_gcs.tif"

    # Create the phase image
    if proj is None:
        gdal.Translate("phase.tif","filt_topophase.unw.geo",bandList=[2],creationOptions = ['COMPRESS=PACKBITS'])
        shutil.copy("phase.tif",gcsname)        
    else:
        print("Creating tmp.tif")
        gdal.Translate("tmp.tif","filt_topophase.unw.geo.vrt",bandList=[2],creationOptions = ['COMPRESS=PACKBITS'])
        print("phase.tif")
        gdal.Warp("phase.tif","tmp.tif",dstSRS=proj,xRes=res,yRes=res,resampleAlg="cubic",dstNodata=0,creationOptions=['COMPRESS=LZW'])
        print("mv tmp.tif {}".format(gcsname))
        shutil.copy("tmp.tif",gcsname)
#        os.remove("tmp.tif")

        print("Creating browse image colorized_unw.png")
        create_browse("unw.png","colorized_unw.png","colorized_unw.png.aux.xml",gcsname,proj,1024)
        create_browse("unw.png","colorized_unw_large.png","colorized_unw_large.png.aux.xml",gcsname,proj,2048)

        print("Creating browse image color.png")
        create_browse("col.png","color.png","color.png.aux.xml",gcsname,proj,1024)
        print("Creating browse image color_large.png")
        create_browse("col.png","color_large.png","color_large.png.aux.xml",gcsname,proj,2048)


    # Create the amplitude image
    if proj is None:
        gdal.Translate("amp.tif","filt_topophase.unw.geo",bandList=[1],creationOptions = ['COMPRESS=PACKBITS'])
    else:
        gdal.Translate("tmp.tif","filt_topophase.unw.geo.vrt",bandList=[1],creationOptions = ['COMPRESS=PACKBITS'])
        gdal.Warp("amp.tif","tmp.tif",dstSRS=proj,xRes=res,yRes=res,resampleAlg="cubic",dstNodata=0,creationOptions = ['COMPRESS=LZW'])
        os.remove("tmp.tif")
    
    # Create the coherence image
    if proj is None:
        gdal.Translate("coherence.tif","phsig.cor.geo",creationOptions = ['COMPRESS=PACKBITS'])
    else:
        gdal.Translate("tmp.tif","phsig.cor.geo.vrt",creationOptions = ['COMPRESS=PACKBITS'])
        gdal.Warp("coherence.tif","tmp.tif",dstSRS=proj,xRes=res,yRes=res,resampleAlg="cubic",dstNodata=0,creationOptions = ['COMPRESS=LZW'])
        os.remove("tmp.tif")


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument("-p","--proj",help="Projection code to convert to")
    parser.add_argument("-r","--res",type=float,help="Resolution for projection")
    args = parser.parse_args()

    convert_files(True,proj=args.proj,res=args.res)


if __name__ == "__main__":
    main()
