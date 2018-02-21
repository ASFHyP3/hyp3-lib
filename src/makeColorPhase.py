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


def makeColorPhase(inFile,rateReduction=1,shift=0,amp=None):
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

    fileName = inFile.replace(".tif","_rgb.tif")
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
    parser.add_argument('geotiff', help='name of GeoTIFF file (input)')
    parser.add_argument('-r',type=float,help='Reduction factor for phase rate',default=1)
    parser.add_argument('-s',type=float,help='Color cycle shift value (0..2pi)',default=0)
    args = parser.parse_args()

    if not os.path.exists(args.geotiff):
        print('GeoTIFF file (%s) does not exist!' % args.geotiff)
        sys.exit(1)

    makeColorPhase(args.geotiff,rateReduction=args.r,shift=args.s)




