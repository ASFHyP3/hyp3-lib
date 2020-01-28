#!/usr/bin/env python

import re
from lxml import html
import os
from datetime import datetime, timedelta
import sys
import argparse
from verify_opod import verify_opod
import requests
import json
from requests.adapters import HTTPAdapter
from six.moves.urllib.parse import urlparse


class FileException(Exception):
  """Could not download orbit file"""


def getPageContentsESA(url, verify):
    hostname = urlparse(url).hostname
    session = requests.Session()
    session.mount(hostname, HTTPAdapter(max_retries=10))
    page = session.get(url, timeout=60, verify=verify)
    print page
    results = json.loads(page.text)
    print results
    print("Count is {}".format(results['count']))
    files = [] 
    for x in range(0,results['count']): 
      print results['results'][x]
      print results['results'][x]['physical_name']
      files.append(results['results'][x]['physical_name'])
    return(files)


def getPageContents(url, verify):
    hostname = urlparse(url).hostname
    session = requests.Session()
    session.mount(hostname, HTTPAdapter(max_retries=10))
    page = session.get(url, timeout=60, verify=verify)
    tree = html.fromstring(page.content)
    l = tree.xpath('//a[@href]//@href')
    ret = []
    for item in l:
        if 'EOF' in item:
            ret.append(item)
    return ret


def findOrbFile(plat,tm,lst):
    d1 = 0
    best = ''
    for item in lst:
        if 'S1' in item:
            item = item.replace(' ','')
            item1 = item
            this_plat=item[0:3]
            item=item.replace('T','')
            item=item.replace('V','')
            t = re.split('_',item)
            if len(t) > 7:
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
    Granule = os.path.basename(s1Granule)

    # get rid of ending "/" 
    if Granule.endswith("/"):
        Granule = Granule[0:len(granule)-1]

    t = re.split('_+',Granule)
    st = t[4].replace('T','')
    url = url1
    files = getPageContents(url, True)
    plat = Granule[0:3]
    orb = findOrbFile(plat,st,files)
    if orb == '':
        url = url2
        files = getPageContents(url, True)
        orb = findOrbFile(plat,st,files)
    if orb == '':
        error = 'Could not find orbit file on ASF website'
        raise FileException(error)
    return url+orb,orb


def getOrbitFileESA(dataFile):

  prec_url = 'https://qc.sentinel1.eo.esa.int/aux_poeorb/'
  rest_url = 'https://qc.sentinel1.eo.esa.int/aux_resorb/'
  precise    = 'https://qc.sentinel1.eo.esa.int/api/v1/?product_type=AUX_POEORB&'
  restituted = 'https://qc.sentinel1.eo.esa.int/api/v1/?product_type=AUX_RESORB&'

  t = re.split('_+',dataFile)
  plat = dataFile[0:3]
  st = t[4].replace('T','')
  et = t[5].replace('T','')

  year = st[0:4]
  month = st[4:6]
  day = st[6:8]
  hour = st[8:10]
  minute = st[10:12]
  second = st[12:14]
 
  start_time = datetime.strptime("{}-{}-{}T{}:{}:{}".format(year,month,day,hour,minute,second),'%Y-%m-%dT%H:%M:%S')
  print("Looking for validity stop of {}".format(start_time))
 
  year = et[0:4]
  month = et[4:6]
  day = et[6:8]
  hour = et[8:10]
  minute = et[10:12]
  second = et[12:14]
 
  end_time = datetime.strptime("{}-{}-{}T{}:{}:{}".format(year,month,day,hour,minute,second),'%Y-%m-%dT%H:%M:%S')
  print("Looking for validity start of {}".format(end_time))
 
  url = precise+'validity_stop__gt='+start_time.strftime('%Y-%m-%dT%H:%M:%S')+'&validity_start__lt='+end_time.strftime('%Y-%m-%dT%H:%M:%S')
  print("Using url {}".format(url))
  files = getPageContentsESA(url, False)
  print("Files found: {}".format(files))
  if len(files) > 0:
    orbitFile = findOrbFile(plat, st, files)
    if len(orbitFile)>0:
      url = prec_url+orbitFile
  else:
    url = restituted+'validity_stop__gt='+start_time.strftime('%Y-%m-%dT%H:%M:%S')+'&validity_start__lt='+end_time.strftime('%Y-%m-%dT%H:%M:%S')
    print("Using url {}".format(url))
    files = getPageContentsESA(url, False)
    print("Files found: {}".format(files))
    if len(files) > 0:
      orbitFile = findOrbFile(plat, st, files)
      if len(orbitFile) > 0:
        url = rest_url+orbitFile
  if len(orbitFile) == 0:
    error = 'Could not find orbit file on ESA website'
    raise FileException(error)

  return url, orbitFile



def fetchOrbitFile(urlOrb,stateVecFile,verify):
  hostname = urlparse(urlOrb).hostname
  session = requests.Session()
  session.mount(hostname, HTTPAdapter(max_retries=10))
  request = session.get(urlOrb, timeout=60, verify=verify)
  f = open(stateVecFile, 'w')
  f.write(request.text)
  f.close()



# Specify provider 
def downloadSentinelOrbitFileProvider(granule, provider, directory):

  if provider.upper() == 'ASF':
    urlOrb, fileNameOrb = getOrbFile(granule)
    verify = True
  elif provider.upper() == 'ESA':
    urlOrb, fileNameOrb = getOrbitFileESA(granule)
    verify = False

  if directory:
    stateVecFile = os.path.join(directory, fileNameOrb)
  else:
    stateVecFile = fileNameOrb

  if not os.path.isfile(stateVecFile):
    if len(stateVecFile) > 0:
      fetchOrbitFile(urlOrb,stateVecFile,verify)
      return stateVecFile
    else:
      return None
  else:
    print("Using existing orbit file; provider unknown")
    provider = "UNKNOWN"
    return stateVecFile


# Main entry point - prefer ASF; failover to ESA
def downloadSentinelOrbitFile(granule,directory=None):
    try:
        stateVecFile=downloadSentinelOrbitFileProvider(granule,'ASF',directory)
        provider = "ASF"
        print("Found state vector file at ASF")
    except:
        print("Unable to find statevector at ASF; trying ESA")
        try:
            stateVecFile = downloadSentinelOrbitFileProvider(granule,'ESA',directory) 
            provider = "ESA"
            print("Found state vector file at ESA")
        except:
            print("Unable to find requested state vector file")
            provider = "NA"
            return None,provider
    
    verify_opod(stateVecFile)
    return(stateVecFile,provider)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog="get_orb.py",description="Get Sentinel-1 orbit file(s) from ASF or ESA website")
    parser.add_argument("safeFiles",help="Sentinel-1 SAFE file name(s)",nargs="*")
    parser.add_argument("-p","--provider",choices=['asf','esa'],help="Name of orbit file server organization")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()

    provider = args.provider
    for g in args.safeFiles: 
        if provider:
            stVecFile = downloadSentinelOrbitFileProvider(g,provider,None)         
        else:
            stVecFile,provider = downloadSentinelOrbitFile(g)
        print("Downloaded orbit file {} from {}".format(stVecFile,provider.upper()))
