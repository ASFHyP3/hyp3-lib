#!/usr/bin/env python
"""Get Sentinel-1 orbit file(s) from ASF or ESA website"""

from __future__ import print_function, absolute_import, division, unicode_literals

import re
from lxml import html
import os
from datetime import datetime, timedelta
import argparse
from hyp3lib.verify_opod import verify_opod
import requests
from requests.adapters import HTTPAdapter
from six.moves.urllib.parse import urlparse


class FileException(Exception):
  """Could not download orbit file"""


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
        Granule = Granule[0:len(Granule)-1]

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

  precise = 'https://qc.sentinel1.eo.esa.int/aux_poeorb/'
  restituted = 'https://qc.sentinel1.eo.esa.int/aux_resorb/'

  year = os.path.basename(dataFile)[17:21]
  month = os.path.basename(dataFile)[21:23]
  day = os.path.basename(dataFile)[23:25]
  date = datetime.strptime(year+'-'+month+'-'+day, '%Y-%m-%d')

  t = re.split('_+',dataFile)
  st = t[4].replace('T','')
  plat = dataFile[0:3]

  start_time = date - timedelta(days=1)
  url = precise+'?validity_start_time='+start_time.strftime('%Y-%m-%d')
  files = getPageContents(url, False)
  if len(files) > 0:
    orbitFile = findOrbFile(plat, st, files)
    url = precise+orbitFile
  else:
    start_time = date
    for page in range(1, 5):
      url = ('{0}?page={1}&validity_start_time={2}'.format(restituted, page,
        start_time.strftime('%Y-%m-%d')))
      files = getPageContents(url, False)
      if len(files) > 0:
        orbitFile = findOrbFile(plat, st, files)
        if len(orbitFile) > 0:
          url = restituted+orbitFile
          break
  if len(orbitFile) == 0:
    error = 'Could not find orbit file on ESA website'
    raise FileException(error)

  return url, orbitFile
  

def downloadSentinelOrbitFile(granule, provider, directory):

  if provider.upper() == 'ASF':
    urlOrb, fileNameOrb = getOrbFile(granule)
    verify = True
  elif provider.upper() == 'ESA':
    urlOrb, fileNameOrb = getOrbitFileESA(granule)
    verify = False

  if len(fileNameOrb) > 0:
    hostname = urlparse(urlOrb).hostname
    session = requests.Session()
    session.mount(hostname, HTTPAdapter(max_retries=10))
    request = session.get(urlOrb, timeout=60, verify=verify)
    stateVecFile = os.path.join(directory, fileNameOrb)
    f = open(stateVecFile, 'w')
    f.write(request.text)
    f.close()
    return stateVecFile
  else:
    return None


# For whatever reason, I can not make the above routine work correctly
# Thus I wrote another using wget instead of request
def downloadSentinelOrbitFile_2(granule):

    try:
        urlOrb, fileNameOrb = getOrbFile(granule)
        cmd = 'wget ' + urlOrb
        os.system(cmd)
        provider = "ASF"
        print("Found state vector file at ASF")
    except:
        print("Unable to find statevector at ASF; trying ESA")
        try:
            urlOrb, fileNameOrb = getOrbitFileESA(granule)
            cmd = 'wget ' + urlOrb 
            os.system(cmd)
            provider = "ESA"
            print("Found state vector file at ESA")
        except:
            print("Unable to find requested state vector file")
            provider = "NA"
            return None,provider
    
    verify_opod(fileNameOrb)
    return(fileNameOrb,provider)


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument("safeFile", help="Sentinel-1 SAFE file name", nargs="*")
    args = parser.parse_args()

    for safe in args.safeFile:
        stVecFile, provider = downloadSentinelOrbitFile_2(safe)
        print("Downloaded orbit file {} from {}".format(stVecFile, provider))

        # print("Getting: " + g)
        # (orburl,f1) = getOrbFile(g)
        # print(orburl)
        # cmd = 'wget ' + orburl
        # os.system(cmd)


if __name__ == "__main__":
    main()
