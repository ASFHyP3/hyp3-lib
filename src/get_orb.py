#!/usr/bin/env python

import re
import requests
from lxml import html
import os
import datetime
import sys
import argparse

def getPageContents(url):
    page = requests.get(url)
    tree = html.fromstring(page.content)
    l = tree.xpath('//a[@href]/text()')
    ret = []
    for item in l:
        if 'EOF' in item:
            ret.append(item)
    return ret

def findOrbFile(plat,tm,lst):
    d1 = 0
    best = ''
    for item in lst:
        item = item.replace(' ','')
        item1 = item
        this_plat=item[0:3]
        item=item.replace('T','')
        item=item.replace('V','')
        t = re.split('_',item)
        start = t[6]
        end = t[7].replace('.EOF','')
        if start < tm and end > tm and plat == this_plat:
            d = ((int(tm)-int(start))+(int(end)-int(tm)))/2
            if d>d1:
                best = item1.replace(' ','')
    return best

def getOrbFile(s1Granule):
    url1 = 'https://s1qc.asf.alaska.edu/aux_poeorb/'
    url2 = 'https://s1qc.asf.alaska.edu/aux_resorb/'
    t = re.split('_+',s1Granule)
    st = t[4].replace('T','')
    # Try url1
    url = url1
    files = getPageContents(url)
    plat = s1Granule[0:3]
    orb = findOrbFile(plat,st,files)
    if orb == '':
        url = url2
        files = getPageContents(url)
        orb = findOrbFile(plat,st,files)
    if orb == '':
        print("ERROR: Orbit file not found!!!")
	sys.exit(-1)
    return url+orb,orb

if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog="get_orb.py",description="Get a Sentinel-1 orbit file from ASF website")
    parser.add_argument("safeFile",help="Sentinel-1 SAFE file name",nargs="*")
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()

    for g in sys.argv[1:]:
        print "Getting: " + g
        (orburl,f1) = getOrbFile(g)
        print orburl
        cmd = 'wget ' + orburl
        os.system(cmd)

