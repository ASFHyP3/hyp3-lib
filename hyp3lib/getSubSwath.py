from __future__ import print_function, absolute_import, division, unicode_literals

import os
from osgeo import ogr
import glob
from lxml import etree

def get_bounding_box_file(safeFile):
    mydir = "%s/annotation" %  safeFile
    myxml = ""
    name = ""

    # Get corners from first and last swath
    name = "001.xml"
    for myfile in os.listdir(mydir):
        if name in myfile:
            myxml = "%s/annotation/%s" % (safeFile,myfile)
    (lat1_max,lat1_min,lon1_max,lon1_min) = get_bounding_box(myxml)

    name = "003.xml"
    for myfile in os.listdir(mydir):
        if name in myfile:
            myxml = "%s/annotation/%s" % (safeFile,myfile)
    (lat2_max,lat2_min,lon2_max,lon2_min) = get_bounding_box(myxml)

    if ((lon1_max-lon2_max)>180) or ((lon1_min-lon2_min)>180):
        if lon1_max < 0: 
            lon1_max += 360
        if lon1_min < 0: 
            lon1_min += 360
        if lon2_max < 0: 
            lon2_max += 360
        if lon2_min < 0: 
            lon2_min += 360

    lat_max = max(lat1_max,lat1_min,lat2_max,lat2_min)
    lat_min = min(lat1_max,lat1_min,lat2_max,lat2_min)
    lon_max = max(lon1_max,lon1_min,lon2_max,lon2_min)
    lon_min = min(lon1_max,lon1_min,lon2_max,lon2_min)

    if (lon_min <= -177 and lon_max>177):
        lat_max = lat_max - 0.15
        lat_min = lat_min + 0.15
        lon_max = lon_max - 0.15
        lon_min = lon_min + 0.15
    else:
        lat_max = lat_max + 0.15
        lat_min = lat_min - 0.15
        lon_max = lon_max + 0.15
        lon_min = lon_min - 0.15

    return lat_max,lat_min,lon_max,lon_min


def get_bounding_box(myxml):
    lon_max = -180
    lon_min = 360
    lat_max = -90
    lat_min = 90
    lon = []
    root = etree.parse(myxml)
    for coord in root.iter('latitude'):
        lat_max = max(float(coord.text),lat_max)
        lat_min = min(float(coord.text),lat_min)
    for coord in root.iter('longitude'):
        lon.append(float(coord.text))
    lon_max = max(lon)
    lon_min = min(lon)
    diff = lon_max - lon_min
    if diff > 180:
        for ii in range(len(lon)):
          if lon[ii] < 0:
            lon[ii] += 360
        lon_min = min(lon)
        lon_max = max(lon)

    return lat_max,lat_min,lon_max,lon_min


###############################################################################
# selectSubswath
#
# Purpose:  Figure out the best subswath a given bounding box lies in.
# Returns:  1-3 for a valid subswath or 0 if not a valid overlap
#
###############################################################################
def SelectSubswath(safeFile,lon_min,lat_min,lon_max,lat_max):

    os.chdir(safeFile)
    os.chdir("annotation")
    for myfile in os.listdir("."):
        if "001.xml" in myfile:
            (lat_max1,lat_min1,lon_max1,lon_min1) = get_bounding_box(myfile)
        if "002.xml" in myfile:
            (lat_max2,lat_min2,lon_max2,lon_min2) = get_bounding_box(myfile)
        if "003.xml" in myfile:
            (lat_max3,lat_min3,lon_max3,lon_min3) = get_bounding_box(myfile)
    os.chdir("../../")

    wkt1 = "POLYGON ((%s %s, %s %s, %s %s, %s %s, %s %s))" % (lat_min,lon_min,lat_max,lon_min,lat_max,lon_max,lat_min,lon_max,lat_min,lon_min)
    wkt2 = "POLYGON ((%s %s, %s %s, %s %s, %s %s, %s %s))" % (lat_min1,lon_min1,lat_max1,lon_min1,lat_max1,lon_max1,lat_min1,lon_max1,lat_min1,lon_min1)
    wkt3 = "POLYGON ((%s %s, %s %s, %s %s, %s %s, %s %s))" % (lat_min2,lon_min2,lat_max2,lon_min2,lat_max2,lon_max2,lat_min2,lon_max2,lat_min2,lon_min2)
    wkt4 = "POLYGON ((%s %s, %s %s, %s %s, %s %s, %s %s))" % (lat_min3,lon_min3,lat_max3,lon_min3,lat_max3,lon_max3,lat_min3,lon_max3,lat_min3,lon_min3)

    poly0 = ogr.CreateGeometryFromWkt(wkt1)
    poly1 = ogr.CreateGeometryFromWkt(wkt2)
    poly2 = ogr.CreateGeometryFromWkt(wkt3)
    poly3 = ogr.CreateGeometryFromWkt(wkt4)

    intersect1 = poly0.Intersection(poly1)
    area1 = intersect1.GetArea()

    intersect2 = poly0.Intersection(poly2)
    area2 = intersect2.GetArea()

    intersect3 = poly0.Intersection(poly3)
    area3 = intersect3.GetArea()

    ss = 0
    if (area1 > area2):
        if (area1 > area3):
            ss = 1
            i = intersect1
        else:
            ss = 3
            i = intersect3
    else:
        if (area2 > area3):
            ss = 2
            i = intersect2
        else:
            if (area3 > 0):
                ss = 3
                i = intersect3

    return ss, i.GetEnvelope()


###############################################################################
# get_real_cc
#
# Purpose:  Get the actual corner coordinates of a Sentinel1 xml file
# Returns:  lists of lat, lon for each corner
# :
#         pt1---------------pt4
#         /                /
#        /                /
#       /                /
#      /                /
#     /                /
#    /                /
#  pt2---------------pt3
#
###############################################################################

def get_real_cc(myxml):

    lats = []
    lons = []

    root = etree.parse(myxml)
    for i in root.iter('numberOfSamples'):
        ns = int(i.text)

    for i in root.iter('numberOfLines'):
        nl = int(i.text)

    for i in root.iter('geolocationGridPoint'):
        line = int(i[2].text)
        samp = int(i[3].text)
        if samp==0 and line==0:
            lats.append(i[4].text)
            lons.append(i[5].text)

    for i in root.iter('geolocationGridPoint'):
        line = int(i[2].text)
        samp = int(i[3].text)
        # the last line is sometimes nl, sometimes nl-1
        if samp==0 and (abs(line-nl) <= 1):
            lats.append(i[4].text)
            lons.append(i[5].text)
            
    for i in root.iter('geolocationGridPoint'):
        line = int(i[2].text)
        samp = int(i[3].text)
        # the last line is sometimes nl, sometimes nl-1
        if samp==ns-1 and (abs(line-nl) <= 1):
            lats.append(i[4].text)
            lons.append(i[5].text)

    for i in root.iter('geolocationGridPoint'):
        line = int(i[2].text)
        samp = int(i[3].text)
        if samp==ns-1 and line==0:
            lats.append(i[4].text)
            lons.append(i[5].text)
                        
    if len(lats) != 4 or len(lons) != 4:
        print("ERROR: Unable to find corner points!")
        exit(1)
    return lats, lons

###############################################################################
# SelectAllSubswaths
#
# Purpose: Find all subswaths that overlap with the given bounding box
# Returns: List of subswath numbers and bounding boxes of the intersections
#
###############################################################################

def SelectAllSubswaths(safeFile,lon_min,lat_min,lon_max,lat_max):

    # Get the real corner coordinates of each subswath
    fi = glob.glob("%s/annotation/*001.xml" % safeFile)[0]
    lats1, lons1 = get_real_cc(fi)

    fi = glob.glob("%s/annotation/*002.xml" % safeFile)[0]
    lats2, lons2 = get_real_cc(fi)

    fi = glob.glob("%s/annotation/*003.xml" % safeFile)[0]
    lats3, lons3 = get_real_cc(fi)

    # Create polygons
    wkt1 = "POLYGON ((%s %s, %s %s, %s %s, %s %s, %s %s))" % (lat_min,lon_min,lat_max,lon_min,lat_max,lon_max,lat_min,lon_max,lat_min,lon_min)
    wkt2 = "POLYGON ((%s %s, %s %s, %s %s, %s %s, %s %s))" % (lats1[0],lons1[0],lats1[1],lons1[1],lats1[2],lons1[2],lats1[3],lons1[3],lats1[0],lons1[0])
    wkt3 = "POLYGON ((%s %s, %s %s, %s %s, %s %s, %s %s))" % (lats2[0],lons2[0],lats2[1],lons2[1],lats2[2],lons2[2],lats2[3],lons2[3],lats2[0],lons2[0])
    wkt4 = "POLYGON ((%s %s, %s %s, %s %s, %s %s, %s %s))" % (lats3[0],lons3[0],lats3[1],lons3[1],lats3[2],lons3[2],lats3[3],lons3[3],lats3[0],lons3[0])

    poly0 = ogr.CreateGeometryFromWkt(wkt1)
    poly1 = ogr.CreateGeometryFromWkt(wkt2)
    poly2 = ogr.CreateGeometryFromWkt(wkt3)
    poly3 = ogr.CreateGeometryFromWkt(wkt4)

    # Calculate intersections
    intersect1 = poly0.Intersection(poly1)
    area1 = intersect1.GetArea()

    intersect2 = poly0.Intersection(poly2)
    area2 = intersect2.GetArea()

    intersect3 = poly0.Intersection(poly3)
    area3 = intersect3.GetArea()

    ss = []
    polygon = []

    if area1 > 0.0:
        ss.append(1)
        polygon.append(intersect1.GetEnvelope())
   
    if area2 > 0.0:
        ss.append(2)
        polygon.append(intersect2.GetEnvelope())
        
    if area3 > 0.0:
        ss.append(3)
        polygon.append(intersect3.GetEnvelope())
        
    return ss, polygon
