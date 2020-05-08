"""Create a colorize phase file from a phase geotiff"""

from __future__ import print_function, absolute_import, division, unicode_literals

import os
import math
import numpy as np
import argparse
from hyp3lib import saa_func_lib as saa
import colorsys
from osgeo import gdal
from hyp3lib.cutGeotiffs import cutFiles

def get2sigmacutoffs(fi):
    (x,y,trans,proj,data) = saa.read_gdal_file(saa.open_gdal_file(fi))
    top = np.percentile(data,98)
    data[data>top]=top
    stddev = np.std(data)
    mean = np.mean(data)
    lo = mean - 2*stddev
    hi = mean + 2*stddev
    return lo,hi

def createAmp(fi):
    (x,y,trans,proj,data) = saa.read_gdal_file(saa.open_gdal_file(fi))
    ampdata = np.sqrt(data)
    outfile = fi.replace('.tif','-amp.tif')
    print(outfile)
    saa.write_gdal_file_float(outfile,trans,proj,ampdata)
    return outfile

def makeColorPhase(inFile,rateReduction=1,shift=0,ampFile=None,scale=0,table='CMY'):

    samples = 1024

    pinf = float('+inf')
    ninf = float('-inf')
    # fnan = float('nan')

    mod2pi = False 
    if table=='CMY':
        mod2pi = True
        R, G, B = makeCycleColor(samples)
    elif table=='RYB' :
        R, G, B = makeContinuousColor(samples)
    elif table=='RWB':
        R, G, B = makeRWBColor(samples)
    else:
        print("ERROR: Unknown color table: {}".format(table))
        exit(1)

    #
    # Read in the phase data    
    #
    x,y,trans,proj= saa.read_gdal_file_geo(saa.open_gdal_file(inFile))
    
    # If data if too big, resize it
    if x > 4096 or y > 4096:
        phaseTmp = "{}_small.tif".format(os.path.basename(inFile.replace(".tif","")))
        gdal.Translate(phaseTmp,inFile,height=4096)
        x,y,trans,proj,data = saa.read_gdal_file(saa.open_gdal_file(phaseTmp))
        print("Created small tif of size {} x {}".format(x, y))
    else:
        x,y,trans,proj,data= saa.read_gdal_file(saa.open_gdal_file(inFile))
        print("Using full size tif of size {} x {}".format(x, y))
        phaseTmp = inFile
        
    # Make a black mask for use after colorization
    mask = np.ones(data.shape,dtype=np.uint8)
    mask[data[:]==0] = 0 

    # Scale to 0 .. samples-1
    data[:] = data[:] + shift
    if mod2pi == True:
        data[:] = data[:] % (2*rateReduction*np.pi)
        const = samples / (2*rateReduction*np.pi)
        data[:] =  data[:] * const
    else:

        mask = np.ones(data.shape,dtype=np.uint8)
        mask[data==pinf] = 0
        mask[data==ninf] = 0 
        mask[np.isnan(data)] = 0 
        data[mask==0]=0


#        mini = np.min(data)
#        maxi = np.max(data)

        mini = np.percentile(data,2)
        maxi = np.percentile(data,98)
        data[data<mini] = mini
        data[data>maxi] = maxi

   
        data[:] = (data[:] - mini) / (maxi - mini)
        data[:] = data * float(samples)

        print(np.max(data))
        print(np.min(data))

        hist = np.histogram(data)
        print(hist[1])
        print(hist[0])

    data[data==samples]=samples-1

    # Convert to integer for indexing
    idata = np.zeros(data.shape,dtype=np.uint16)
    idata[:] = data[:]

    # Make the red, green, and blue versions
    red = np.zeros(data.shape,dtype=np.uint8) 
    green = np.zeros(data.shape,dtype=np.uint8) 
    blue = np.zeros(data.shape,dtype=np.uint8) 

    red = R[idata[:]]
    green = G[idata[:]]
    blue = B[idata[:]]

    # Apply the black mask
    red[mask==0] = 0
    green[mask==0] = 0
    blue[mask==0] = 0

    if ampFile is None:
        # Write out the RGB phase image
        fileName = inFile.replace(".tif","_rgb.tif")
        saa.write_gdal_file_rgb(fileName,trans,proj,red,green,blue)

    # If we have amplitude, use that
    else:
        # Make the red, green, and blue floating point versions
        redf = np.zeros(data.shape)
        greenf = np.zeros(data.shape)
        bluef = np.zeros(data.shape)

         # Scale from 0 .. 1
        redf[::] = red[::]/255.0
        greenf[::] = green[::]/255.0
        bluef[::] = blue[::]/255.0

        # Read in the amplitude data
        x1,y1,trans1,proj1 = saa.read_gdal_file_geo(saa.open_gdal_file(ampFile))

        # If too large, resize the data
        if x1 > 4096 or y1 > 4096:
            ampTmp = "{}_small.tif".format(os.path.basename(ampFile.replace(".tif","")))
            gdal.Translate(ampTmp,ampFile,height=y,width=x)
            x1,y1,trans1,proj1,amp = saa.read_gdal_file(saa.open_gdal_file(ampTmp))
        else:
            x1,y1,trans1,proj1,amp = saa.read_gdal_file(saa.open_gdal_file(ampFile))
            ampTmp = ampFile

        if (x != x1) or (y != y1):
            cutFiles([phaseTmp,ampTmp])
#            if phaseTmp != inFile:
#                os.remove(phaseTmp)
            phaseTmp = phaseTmp.replace(".tif","_clip.tif")
            x,y,trans,proj,data = saa.read_gdal_file(saa.open_gdal_file(phaseTmp))
            
#            if ampTmp != ampFile:
#                os.remove(ampTmp)
            ampTmp = ampTmp.replace(".tif","_clip.tif")
            x1,y1,trans1,proj1,amp = saa.read_gdal_file(saa.open_gdal_file(ampTmp))

        print("Data shape is {}".format(data.shape))
        print("Amp shape is {}".format(amp.shape))

        # Make a black mask for use after colorization
        mask = np.ones(amp.shape,dtype=np.uint8)
        mask[amp==pinf] = 0
        mask[amp==ninf] = 0 
        mask[np.isnan(amp)] = 0 
        amp[mask==0]=0

        ave = np.mean(amp)
        print("Mean of amp data is {}".format(ave))
        amp[mask==0]=ave

        print("AMP HISTOGRAM:")
        hist = np.histogram(amp)
        print(hist[1])
        print(hist[0])

        ave = np.mean(amp)
        print("Amp average is {}".format(ave))
        print("Amp median is {}".format(np.median(amp)))
        print("Amp stddev is {}".format(np.std(amp)))

        # Rescale amplitude to 2-sigma byte range, otherwise may be all dark
        amp2File = createAmp(ampTmp)
        myrange = get2sigmacutoffs(amp2File)
        newFile = "tmp.tif"
        gdal.Translate(newFile,amp2File,outputType=gdal.GDT_Byte,scaleParams=[myrange],resampleAlg="average")
        x,y,trans,proj,amp = saa.read_gdal_file(saa.open_gdal_file(newFile))
#        if ampTmp != ampFile:
#            os.remove(ampTmp)
#        os.remove(amp2File)
#        os.remove(newFile)

        print("2-sigma AMP HISTOGRAM:")
        hist = np.histogram(amp)
        print(hist[1])
        print(hist[0])

        # Scale amplitude from 0.0 to 1.0
        ampf = np.zeros(data.shape)
        ampf = amp / 255.0
        ampf = ampf + float(scale)
        ampf[ampf>1.0]=1.0

        print("SCALED AMP HISTOGRAM:")
        hist = np.histogram(ampf)
        print(hist[1])
        print(hist[0])

        # Perform color transformation 
        h = np.zeros(data.shape)
        l = np.zeros(data.shape)
        s = np.zeros(data.shape)

        for j in range(x):
            for i in range(y):
                h[i,j],l[i,j],s[i,j] = colorsys.rgb_to_hls(redf[i,j],greenf[i,j],bluef[i,j])

        print("LIGHTNESS HISTOGRAM:")
        hist = np.histogram(l)
        print(hist[1])
        print(hist[0])

        l = l * ampf

        print("NEW LIGHTNESS HISTOGRAM:")
        hist = np.histogram(l)
        print(hist[1])
        print(hist[0])

        for j in range(x):
            for i in range(y):
                redf[i,j],greenf[i,j],bluef[i,j] = colorsys.hls_to_rgb(h[i,j],l[i,j],s[i,j]) 

        red = redf * 255
        green = greenf * 255
        blue = bluef * 255

        print("TRANFORMED RED HISTOGRAM:")
        hist = np.histogram(red)
        print(hist[1])
        print(hist[0])

        # Apply mask
        red[mask==0]=0
        green[mask==0]=0
        blue[mask==0]=0

        # Write out the RGB phase image
        fileName = inFile.replace(".tif","_amp_rgb.tif")
        saa.write_gdal_file_rgb(fileName,trans,proj,red,green,blue)


#
# This code makes an image to show off the color table
#
#    rainbow_red = np.zeros((1024,1024),np.uint8)
#    rainbow_green = np.zeros((1024,1024),np.uint8)
#    rainbow_blue = np.zeros((1024,1024),np.uint8)
#    for i in range(1024):
#        for j in range(1024):
#            idx = int((float(i)/1024.0)*samples)
#            rainbow_red[i,j] = R[idx]
#            rainbow_green[i,j] = G[idx]
#            rainbow_blue[i,j] = B[idx]
#    saa.write_gdal_file_rgb("rainbow.tif",trans,proj,rainbow_red,rainbow_green,rainbow_blue)

    return(fileName)        
 

def makeContinuousColor(samples):

    #
    # Make the color LUT
    #
    R = np.zeros(samples,np.uint8)
    G = np.zeros(samples,np.uint8)
    B = np.zeros(samples,np.uint8)
    
    # Going from Red to Yellow
    for i in range (1,samples/3):
        val = i * math.pi / (samples/3)
        R[i] = 255
        G[i] = 128 + math.sin(val+3*math.pi/2)*128
        B[i] = 0

    # Going from Yellow to Green
    for i in range(samples/3,2*samples/3):
        val = i*math.pi/(samples/3)
        R[i] = 128 + math.sin(val+3*math.pi/2)*128
        G[i] = 255
        B[i] = 0

    # Going from Green to Blue 
    for i in range(2*samples/3,samples):
        val = i*math.pi/(samples/3)
        R[i] = 0
        G[i] = 128 + math.sin(val+math.pi/2)*128
        B[i] = 128 + math.sin(val+3*math.pi/2)*128

    R[0] = 255
    R[samples/3] = 255
    G[2*samples/3] = 255
    B[samples-1] = 255 

    R = R[::-1]
    G = G[::-1]
    B = B[::-1]
    
    return R, G, B   

def makeRWBColor(samples):

    #
    # Make the color LUT
    #
    R = np.zeros(samples,np.uint8)
    G = np.zeros(samples,np.uint8)
    B = np.zeros(samples,np.uint8)
    
    # Going from Blue to White
    for i in range(samples+1/2):
        val = i * math.pi / (samples/2)
        R[i] = 128 + math.sin(val+3*math.pi/2)*128
        G[i] = 128 + math.sin(val+3*math.pi/2)*128
        B[i] = 255

    # Going from White to Red
    for i in range(samples/2,samples):
        val = i*math.pi/(samples/2)
        R[i] = 255
        G[i] = 128 + math.sin(val+3*math.pi/2)*128
        B[i] = 128 + math.sin(val+3*math.pi/2)*128


    R[samples/2] = 255
    G[samples/2] = 255
    B[samples/2] = 255
    return R, G, B   

def makeCycleColor(samples):

    #
    # Make the color LUT
    #
    R = np.zeros(samples,np.uint8)
    G = np.zeros(samples,np.uint8)
    B = np.zeros(samples,np.uint8)
    
    # Going from Yellow to Cyan
    for i in range (1,samples/3):
        val = i * math.pi / (samples/3)
        G[i] = 255
        R[i] = 128 + math.sin(val+math.pi/2)*128
        B[i] = 128 + math.sin(val+3*math.pi/2)*128

    # Going from Cyan to Magenta
    for i in range(samples/3,2*samples/3):
        val = i*math.pi/(samples/3)
        B[i] = 255
        R[i] = 128 + math.sin(val+math.pi/2)*128
        G[i] = 128 + math.sin(val+3*math.pi/2)*128

    # Going from Magenta to Yellow 
    for i in range(2*samples/3,samples):
        val = i*math.pi/(samples/3)
        R[i] = 255
        B[i] = 128 + math.sin(val+math.pi/2)*128
        G[i] = 128 + math.sin(val+3*math.pi/2)*128

    # Fix holes in color scheme
    G[samples/3] = 255
    B[2*samples/3] = 255
    G[samples-1] = 255 

    return R, G, B


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('geotiff', help='name of GeoTIFF phase file (input)')
    parser.add_argument('-a',help='Ampltiude image to use for intensity')
    parser.add_argument('-c',type=float,help='Scale the amplitude by this value (0-1)',default=0.0)
    parser.add_argument('-r',type=float,help='Reduction factor for phase rate',default=1)
    parser.add_argument('-s',type=float,help='Color cycle shift value (0..2pi)',default=0)
    parser.add_argument('-t',choices=['CMY','RYB','RWB'],help='Name of color table to use (default CMY)',default='CMY')
    args = parser.parse_args()

    if not os.path.exists(args.geotiff):
        print('ERROR: GeoTIFF file (%s) does not exist!' % args.geotiff)
        exit(1)

    if args.a is not None:
        if not os.path.exists(args.a):
            print('ERROR: Amplitude file (%s) does not exist!' % args.a)
            exit(1)

    makeColorPhase(args.geotiff,ampFile=args.a,rateReduction=args.r,shift=args.s,scale=args.c,table=args.t)


if __name__ == '__main__':
    main()
