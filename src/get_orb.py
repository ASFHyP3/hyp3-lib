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
    results = json.loads(page.text)
    print("results : {}".format(results))
    if results['count'] > 0:
        print results['results'][0]['physical_name']
        fileName = results['results'][0]['physical_name']
        url = results['results'][0]['remote_url']
        return(fileName,url)
    else:
        print("WARNING: No results returned from ESA query")
    return(None,None)

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

def dateStr2dateTime(string):
    year = string[0:4]
    month = string[4:6]
    day = string[6:8]
    hour = string[8:10]
    minute = string[10:12]
    second = string[12:14]
    outTime = datetime.strptime("{}-{}-{}T{}:{}:{}".format(year,month,day,hour,minute,second),'%Y-%m-%dT%H:%M:%S')
    return(outTime)
   
def findOrbFile(plat,st,et,lst):
    d1 = timedelta(seconds=0)
    best = ''

    for item in lst:
        if 'S1' in item:
#            item = item.replace(' ','')
            item1 = item
            this_plat=item[0:3]
            item=item.replace('T','')
            item=item.replace('V','')
            t = re.split('_',item)
            if plat == this_plat: 
                if len(t) > 7:
                    start = dateStr2dateTime(t[6])
                    end = dateStr2dateTime(t[7].replace('.EOF',''))
                    if start < st and end > et and plat == this_plat:
                        d = ((st-start)+(end-et))/2
                        if d>d1:
                            best = item1
                            d1 = d
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
    et = t[5].replace('T','')
    url = url1
    files = getPageContents(url, True)
    plat = Granule[0:3]
    orb = findOrbFile(plat,st,et,files)
    if orb == '':
        url = url2
        files = getPageContents(url, True)
        orb = findOrbFile(plat,st,et,files)
    if orb == '':
        error = 'Could not find orbit file on ASF website'
        raise FileException(error)
    return url+orb,orb


def getOrbitFileESA(dataFile):

  prec_url = 'https://qc.sentinel1.eo.esa.int/aux_poeorb/'
  rest_url = 'https://qc.sentinel1.eo.esa.int/aux_resorb/'
  precise    = 'https://qc.sentinel1.eo.esa.int/api/v1/?product_type=AUX_POEORB&ordering=-creation_date&page_size=1&'
  restituted = 'https://qc.sentinel1.eo.esa.int/api/v1/?product_type=AUX_RESORB&ordering=-creation_date&page_size=1&'
  sec60 = timedelta(seconds=60)
  plat = dataFile[0:3]

  t = re.split('_+',dataFile)
  st = t[4].replace('T','')
  et = t[5].replace('T','')

  start_time = dateStr2dateTime(st)
  end_time = dateStr2dateTime(et)

  start_time = start_time - sec60
  end_time = end_time + sec60

  url = precise+'validity_stop__gt='+start_time.strftime('%Y-%m-%dT%H:%M:%S')+'&validity_start__lt='+end_time.strftime('%Y-%m-%dT%H:%M:%S')
  orbitFile,url = getPageContentsESA(url, False)
  if url:
    print("Using url {}".format(url))
  else:
    print("Unable to find POEORB - Looking for RESORB")
    url = restituted+'validity_stop__gt='+start_time.strftime('%Y-%m-%dT%H:%M:%S')+'&validity_start__lt='+end_time.strftime('%Y-%m-%dT%H:%M:%S')
    orbitFile,url = getPageContentsESA(url, False)
    if url:
      print("Using url {}".format(url))
    else:
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
            if stateVecFile:
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
