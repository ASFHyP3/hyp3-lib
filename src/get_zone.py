#!/usr/bin/python
import math

# Get the UTM zone
def get_zone(lon_min,lon_max):
    center_lon = (lon_min+lon_max)/2;
    zf = (center_lon+180)/6+1
    zone = math.floor(zf)
    return zone

