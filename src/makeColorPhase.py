#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
###############################################################################
# makeColorPhase.py
#
# Project:  HYP3 InSAR
# Purpose:  Create a colorized image from phase data
#  
# Author:   Tom Logan
#
# Issues/Caveats:
#
###############################################################################
# Copyright (c) 2018, Alaska Satellite Facility
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
import os
import math
import numpy as np
import argparse
from argparse import RawTextHelpFormatter
import saa_func_lib as saa
import colorsys
from osgeo import gdal

def get2sigmacutoffs(fi):
    (x,y,trans,proj,data) = saa.read_gdal_file(saa.open_gdal_file(fi))
    stddev = np.std(data)
    mean = np.mean(data)
    lo = mean - 2*stddev
    hi = mean + 2*stddev
    del data
    return lo,hi

def createAmp(fi):
    (x,y,trans,proj,data) = saa.read_gdal_file(saa.open_gdal_file(fi))
    ampdata = np.sqrt(data)
    outfile = fi.replace('.tif','-amp.tif')
    print outfile
    saa.write_gdal_file_float(outfile,trans,proj,ampdata)
    return outfile


def makeColorPhase(inFile,rateReduction=1,shift=0,ampFile=None,scale=0):
    #
    # Make the color LUT
    #
    samples = 1024
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

    # Read in the phase data
    x,y,trans,proj,data = saa.read_gdal_file(saa.open_gdal_file(inFile))

    # Make a black mask for use after colorization
    mask = np.ones(data.shape,dtype=np.uint8)
    mask[data[:]==0] = 0 

    # Scale to 0 .. samples-1
    data[:] = data[:] + shift
    data[:] = data[:] % (2*rateReduction*np.pi)
    const = samples / (2*rateReduction*np.pi)
    data[:] =  data[:] * const

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

    # Write out the RGB phase image
    fileName = inFile.replace(".tif","_rgb.tif")
    saa.write_gdal_file_rgb(fileName,trans,proj,red,green,blue)

    # If we have amplitude, use that
    if ampFile is not None:
   
        # Make the red, green, and blue versions
        redf = np.zeros(data.shape)
        greenf = np.zeros(data.shape)
        bluef = np.zeros(data.shape)

        # Scale from 0.0 to 1.0    
        for j in range(x):
            for i in range(y):
                redf[i,j] = float(red[i,j])/255.0
                greenf[i,j] = float(green[i,j])/255.0
                bluef[i,j] = float(blue[i,j])/255.0

        print "RED HISTOGRAM:"
        hist = np.histogram(redf)
        print hist[1]
        print hist[0]

        # Read in the ampltiude data
        x,y,trans,proj,amp = saa.read_gdal_file(saa.open_gdal_file(ampFile))

        pinf = float('+inf')
        ninf = float('-inf')
        fnan = float('nan')
        mask[:] = 1

        mask[amp==pinf] = 0
        mask[amp==ninf] = 0 
        mask[np.isnan(amp)] = 0 
        amp[mask==0]=0

        ave = np.mean(amp)
        print "Mean of amp data is {}".format(ave)
        amp[mask==0]=ave

        print "AMP HISTOGRAM:"
        hist = np.histogram(amp)
        print hist[1]
        print hist[0]

        ave = np.mean(amp)
        print "Amp average is {}".format(ave)
        print "Amp median is {}".format(np.median(amp))
        print "Amp stddev is {}".format(np.std(amp))

        # Rescale amplitude to 2-sigma byte range, otherwise may be all dark
        ampFile = createAmp(ampFile)
        myrange = get2sigmacutoffs(ampFile)
        newFile = "tmp.tif"
        gdal.Translate(newFile,ampFile,outputType=gdal.GDT_Byte,scaleParams=[myrange],resampleAlg="average")
        x,y,trans,proj,amp = saa.read_gdal_file(saa.open_gdal_file(newFile))

        print "2-sigma AMP HISTOGRAM:"
        hist = np.histogram(amp)
        print hist[1]
        print hist[0]

        # Scale amplitude from 0.0 to 1.0
        ampf = np.zeros(data.shape)
        ampf = amp / 255.0
	ampf = ampf + float(scale)
        ampf[ampf>1.0]=1.0
        
        print "SCALED AMP HISTOGRAM:"
        hist = np.histogram(ampf)
        print hist[1]
        print hist[0]

        # Perform color transformation 
        h = np.zeros(data.shape)
        l = np.zeros(data.shape)
        s = np.zeros(data.shape)

        for j in range(x):
            for i in range(y):
                h[i,j],l[i,j],s[i,j] = colorsys.rgb_to_hls(redf[i,j],greenf[i,j],bluef[i,j])
                
        print "LIGHTNESS HISTOGRAM:"
        hist = np.histogram(l)
        print hist[1]
        print hist[0]
                
        l = l * ampf
        
        print "NEW LIGHTNESS HISTOGRAM:"
        hist = np.histogram(l)
        print hist[1]
        print hist[0]

        for j in range(x):
            for i in range(y):
                redf[i,j],greenf[i,j],bluef[i,j] = colorsys.hls_to_rgb(h[i,j],l[i,j],s[i,j]) 

        red = redf * 255
        green = greenf * 255
        blue = bluef * 255
       
        print "TRANFORMED RED HISTOGRAM:"
        hist = np.histogram(red)
        print hist[1]
        print hist[0]

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

if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog='makeColorPhase',
      description='Create a colorize phase file from a phase geotiff',
      formatter_class=RawTextHelpFormatter)
    parser.add_argument('geotiff', help='name of GeoTIFF phase file (input)')
    parser.add_argument('-a',help='Ampltiude image to use for intensity')
    parser.add_argument('-c',type=float,help='Scale the amplitude by this value (0-1)',default=0.0)
    parser.add_argument('-r',type=float,help='Reduction factor for phase rate',default=1)
    parser.add_argument('-s',type=float,help='Color cycle shift value (0..2pi)',default=0)
    args = parser.parse_args()

    if not os.path.exists(args.geotiff):
        print('ERROR: GeoTIFF file (%s) does not exist!' % args.geotiff)
        exit(1)

    if args.a is not None:
        if not os.path.exists(args.a):
            print('ERROR: Amplitude file (%s) does not exist!' % args.a)
            exit(1)

    makeColorPhase(args.geotiff,ampFile=args.a,rateReduction=args.r,shift=args.s,scale=args.c)




