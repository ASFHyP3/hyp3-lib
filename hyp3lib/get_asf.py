
from __future__ import print_function, absolute_import, division, unicode_literals

import csv
import datetime
import hashlib
import logging
import logging.handlers
import mimetypes
import multiprocessing
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback
import zipfile
from optparse import OptionParser

import requests
from lxml import etree
from lxml import html
from six.moves import configparser
from six.moves import queue
from six.moves import range

from hyp3lib import __version__ as _hyp3lib_version

log = logging.getLogger(__file__)
already_fetched = dict()
lock = multiprocessing.Lock()


def get_cla():
    parser = OptionParser(prog='get_asf.py')
    parser.add_option(
        "--debug", action="store_true", dest="debug", help="Print out debug messages"
    )
    parser.add_option(
        "--version", action="store_true", dest="version", help="Print the version number and exit"
    )
    parser.add_option(
        "--platform", action="store", dest="platforms", help="Platform to search for (e.g., ALOS, ERS-1)"
    )
    parser.add_option(
        "--beam-mode", "--beam_mode", "--beammode", action="store", dest="beammodes",
        help="Beam Modes to search for (e.g., FBS, FBD, IW)"
    )
    parser.add_option(
        "--start_time", "--start-time", action="store", dest="start_time",
        help="Start time for the search (format is YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD)"
    )
    parser.add_option(
        "--end_time", "--end-time", action="store", dest="end_time",
        help="End time for the search (format is YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD)"
    )
    parser.add_option(
        "--wkt", action="store", dest="wkt",
        help="Standard WKT string, e.g.: polygon((-119.543 37.925, -118.443 37.7421, -118.682 36.8525, -119.77 37.0352, -119.543 37.925 ))"
    )
    parser.add_option(
        "--point", action="store", dest="point",
        help="A single lon,lat value (e.g.: -155.08,65.82)"
    )
    parser.add_option(
        "--delay", action="store", dest="delayStr",
        help="Seconds between granule fetching (e.g.: 3600, to get a granule once per hour)"
    )
    parser.add_option(
        "--dir", action="store", dest="dataDir", help="Directory to store downloaded granules"
    )
    parser.add_option(
        "--tmp", action="store", dest="tmpDir", help="Directory to store temporary files (default: /tmp)"
    )
    parser.add_option(
        "--user", "--username", action="store", dest="user", help="URS Username"
    )
    parser.add_option(
        "--pass", "--password", action="store", dest="password", help="URS Password"
    )
    parser.add_option(
        "--max", "--max_results", action="store", dest="maxStr", help="Maximum Number of Granules to Return"
    )
    parser.add_option(
        "--resume", action="store_true", dest="resume",
        help="If a file is already present in the download directory, instruct wget to attempt to resume the download of that file."
    )
    parser.add_option(
        "--ignore", action="store_true", dest="ignore",
        help="If a file is already present in the download directory, skip it."
    )
    parser.add_option(
        "--overwrite", "--redownload", action="store_true", dest="overwrite",
        help="If a file is already present in the download directory, download it again."
    )
    parser.add_option(
        "--l0", "--RAW", "--raw", action="store_true", dest="l0",
        help="Download the Level 0 product (L1.0 for PALSAR, RAW for Sentinel) for a granule."
    )
    parser.add_option(
        "--slc", "--SLC", action="store_true", dest="slc",
        help="Download the SLC product (L1.1 for PALSAR) for a granule.  Legacy platforms do not have this product."
    )
    parser.add_option(
        "--l1", "--detected", "--GRD", "--grd", action="store_true", dest="l1",
        help="Download the Level 1 product (L1.5 for PALSAR, GRD for Sentinel) for a granule. (This is the default)"
    )
    parser.add_option(
        "--browse", action="store_true", dest="browse", help="Download the browse image for a product."
    )
    parser.add_option(
        "--rtc", action="store_true", dest="rtc", help="Download the RTC image for a product (PALSAR only)."
    )
    parser.add_option(
        "--verify", action="store_true", dest="verify", help="Verify checksums of downloaded files (Sentinel only)"
    )
    parser.add_option(
        "--max_retry", "--max-retry", "--retries", action="store", dest="max_retries", help="How many times to retry a failed download"
    )
    parser.add_option(
        "--wget_options", "--wget-options", action="store", dest="wget_options", help="Adds options to the wget commands responsible for downloading files. For example '--no-check-certificate' should be used if an invalid certificate is preventing downloading."
    )
    parser.add_option(
        "--threads", action="store", dest="threads_num", default=1, type="int", help="Specifies the number of threads to be used for downloading; default is 1."
    )
    parser.add_option(
        "--already-fetched-file", "--already-fetched-list", "--already_fetched_file", "--already_fetched_list",
        action="store", dest="already_fetched_file", help="Specify a text file of granules that have already been downloaded."
    )
    parser.add_option(
        "--get-orb", action="store_true", dest="get_orb", help="Also download the Sentinel Precise or Restituted orbits files"
    )
    parser.add_option(
        "--dry-run", action="store_true", dest="dry_run", help="Don't download anything, just print granules that would be downloaded"
    )
    options, args = parser.parse_args()
    return options, args


def setup_logger(dbg):
    if dbg:
        lvl = logging.DEBUG
    else:
        lvl = logging.INFO
    log.setLevel(lvl)

    handler_stream = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter('%(asctime)s [%(threadName)s] [%(levelname)s] %(message)s')
    handler_stream.setFormatter(formatter)

    handler_stream.setLevel(lvl)
    log.addHandler(handler_stream)

def get_config(cfg):
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "config"))

    cfg_file = None
    if os.path.isfile(os.path.join(cfg_path, 'get_asf.cfg')):
        cfg_file = os.path.join(cfg_path, 'get_asf.cfg')
    elif os.path.isfile(os.path.join(os.path.expanduser("~"), ".get_asf.cfg")):
        cfg_file = os.path.join(os.path.expanduser("~"), ".get_asf.cfg")
    elif os.path.isfile(os.path.join(os.path.expanduser("~"), ".hyp3", "get_asf.cfg")):
        cfg_file = os.path.join(os.path.expanduser("~"), ".hyp3", "get_asf.cfg")
    elif os.path.isfile(os.path.join(os.path.expanduser("~"), "get_asf.cfg")):
        cfg_file = os.path.join(os.path.expanduser("~"), "get_asf.cfg")
    elif os.path.isfile(os.path.join(os.path.abspath(os.path.dirname(__file__)), "get_asf.cfg")):
        cfg_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), "get_asf.cfg")
    elif os.path.isfile("get_asf.cfg"):
        cfg_file = "get_asf.cfg"

    if cfg_file is not None:
        config = configparser.ConfigParser()
        config.read(cfg_file)

        if cfg.user is None and config.has_option('general', 'user'): cfg.user = config.get('general', 'user')
        if cfg.user is None and config.has_option('general', 'username'): cfg.user = config.get('general', 'username')
        if cfg.password is None and config.has_option('general', 'password'): cfg.password = config.get('general', 'password')
        if cfg.password is None and config.has_option('general', 'pass'): cfg.password = config.get('general', 'pass')
        if cfg.dataDir is None and config.has_option('general', 'dir'): cfg.dataDir = config.get('general', 'dir')
        if cfg.tmpDir is None and config.has_option('general', 'tmp'): cfg.tmpDir = config.get('general', 'tmp')
        if cfg.max_retries is None and config.has_option('general', 'max_retries'): cfg.max_retries = config.get('general', 'max_retries')
        if cfg.wget_options is None and config.has_option('general', 'wget_options'): cfg.wget_options = config.get('general', 'wget_options')
        if cfg.threads_num is None and config.has_option('general', 'threads'):
            cfg.threads_num = int(config.get('general', 'threads'))
        elif cfg.threads_num is None: cfg.threads_num = 1
        if cfg.already_fetched_file is None and config.has_option('general', 'already_fetched_file'):
            cfg.already_fetched_file = config.get('general', 'already_fetched_file')
        if cfg.already_fetched_file is None and config.has_option('general', 'already_fetched_list'):
            cfg.already_fetched_file = config.get('general', 'already_fetched_list')
        if not cfg.get_orb and config.has_option('general', 'get_orb'):
            cfg.get_orb = bool(config.get('general', 'get_orb'))
        if cfg.dry_run:
            cfg.threads_num = 1
    return cfg

def get_already_fetched(filename):
    if filename is not None:
        if os.path.isfile(filename):
            log.info('Reading list of already fetched granules: ' + filename)

            num = 0
            with open(filename, 'r') as fl:
                for line in fl:
                    already_fetched[line.rstrip()] = 1
                    num += 1

            log.info('Already fetched: ' + str(num) + ' files.')
        else:
            log.info('Already fetched list does not exist, will be created.')


def add_to_fetched(filename, granule):
    with lock:
        if filename is not None:
            f = open(filename, 'a')
            f.write(granule + '\n')
            f.close()

        already_fetched[granule] = 1


def guess_platform(s):
    if s is None or len(s) == 0:
        return None

    plat = None
    #log.debug("Checking: '" + repr(s) + "'")
    if re.search("^S1[ABCD]_", s):
        plat = "Sentinel"
    elif re.search("^ALPSRP\d{9}", s):
        plat = "PALSAR"
    elif re.search("^AP_", s):
        plat = "PALSAR"
    elif re.search("^[JRE][12]", s):
        plat = s[0:2]
    elif re.search("^SS", s):
        plat = "SEASAT"
    elif re.search("^UA", s):
        plat = "UAVSAR"
    elif re.search("^AI", s):
        plat = "AIRMOSS"
    else:
        #log.warning(s + ": Not recognized")
        pass
    #log.debug(s + ": " + str(plat))

    return plat

def str_for_plat_lvl(platform, level):
    if level == "BROWSE":
        return level

    h = {
        "Sentinel-L0"  : "RAW",
        "Sentinel-SLC" : "SLC",
        "Sentinel-L1"  : "GRD",
        "PALSAR-L0"    : "L1.0",
        "PALSAR-SLC"   : "L1.1",
        "PALSAR-L1"    : "L1.5",
        "PALSAR-RTC"   : "RTC_HI_RES",
    }

    k = platform+"-"+level
    log.debug('key: '+k)
    if k in h:
        return h[k]
    else:
        return level

def getPageContents(url):
    page = requests.get(url)
    tree = html.fromstring(page.content)
    l = tree.xpath('//a[@href]/text()')
    ret = []
    for item in l:
        if 'EOF' in item:
            ret.append(item)
    return ret

def findOrbFile(tm,lst):
    d1 = 0
    best = ''
    for item in lst:
        item1 = item
        item=item.replace('T','')
        item=item.replace('V','')
        t = re.split('_',item)
        start = t[6]
        end = t[7].replace('.EOF','')
        if start < tm and end > tm:
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
    orb = findOrbFile(st,files)
    if orb == '':
        url = url2
        files = getPageContents(url)
        orb = findOrbFile(st,files)
    return url+orb,orb

def get_orb(s1Granule):
    (orburl,orbfile) = getOrbFile(s1Granule)
    if 'resorb' in orburl:
        log.info('Getting restituted orbit for ' + s1Granule + ': ' + orbfile)
    elif 'poeorb' in orburl:
        log.info('Getting precise orbit for ' + s1Granule + ': ' + orbfile)
    else:
        log.warning('No restituted or precise orbit found for ' + s1Granule)
        return

    cmd = 'wget ' + orburl
    execute(cmd)

def execute_error(msg, raise_on_error):
    if raise_on_error:
        raise Exception(msg)
    else:
        log.error(msg)

def execute(cmd, expected=None, quiet=False, raise_on_error=False):
    """
    Executes the specified script and returns its output.

    An exception is thrown if the script's exit code is non-zero, or the "expected" output
    file isn't found.  In those situations the output is inspected to try to find a useful error
    string to use as the Exception text.

    Params:
        cmd: Command-line to run.
        expected: A filename the script should generate.  The function checks for the existence
            of this file after the script completes, errors out of it isn't found.  When None,
            this check is skipped.
        quiet: If True, output from the script is not echoed.

    Returns:
        string containing the output of the script that was run.
    """

    log.debug('Running command: ' + cmd)
    rcmd = cmd + ' 2>&1'

    pipe = subprocess.Popen(rcmd, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
    output = pipe.communicate()[0]
    return_val = pipe.returncode
    log.debug('subprocess return value was ' + str(return_val))

    for line in output.split('\n'):
        if not quiet and len(line.rstrip()) > 0:
            log.debug('Proc: ' + line)

    if not quiet:
        log.debug('Finished: ' + cmd)

    if return_val != 0:
        if 'wget' in cmd and return_val == -2:
            # ctrl-c
            raise Exception("Ctrl-C pressed")
        log.debug('Nonzero return value!')
        tool = cmd.split(' ')[0]
        last = 'Nonzero return value: ' + str(return_val)
        found = False
        for l in output.split('\n'):
            line = l.strip()
            if len(line) > 0:
                last = line
                if 'ERROR' in line.upper():
                    execute_error(tool + ': ' + line, raise_on_error)
                    found = True

        if not found:
            # No error line found, die with last line
            execute_error(tool + ': ' + last, raise_on_error)

        ok = False

    else:
        ok = True

    if expected is not None:
        log.debug('Checking for expected output: ' + expected)
        if os.path.isfile(expected):
            log.debug('Found: ' + expected)
        else:
            execute_error("Expected output file not found: " + expected, raise_on_error)
            ok = False

    return output, ok


def find_granules_file(i, granules, cfg):
    if os.path.isfile(granules) and (mimetypes.guess_type(granules)[0] == 'text/plain' or mimetypes.guess_type(granules)[0] == 'text/csv'):
        log.info("Opening " + granules)
        with open(granules, 'r') as fl:
            granule_list = fl.read().replace('\n', ' ').replace('\r', ' ').replace('<',' ').replace('>',' ').replace('/', ' ')
        return find_granules_list(i, granule_list, cfg)
    else:
        log.info("Adding " + granules)
        return find_granules_list(i, granules, cfg)


def fudge_level(g, l):
    if l is not None:
        return l
    if 'S1' in g:
        if 'GRD' in g: return 'L1'
        if 'SLC' in g: return 'SLC'
        if 'RAW' in g: return 'L0'
        if 'OCN' in g: return 'OCN'
    return 'L1'


def zpad6(i):
    return "00000"+str(i)[-6:]


def valid_granule(g):
    pr = {
           "Sentinel-1": r'S1[ABCD]_\w{2}_\w{4}_\w{4}_\d{8}T\d{6}_\d{8}T\d{6}_\d{6}_\w{6}_\w{4}',
           "PALSAR":     r'ALPSRP\d{9}',
           "Legacy":     r'[JER][12]_\d{5}_\w{3}_F\d+'
         }

    if g[0:2] == "S1":
        exp = pr["Sentinel-1"]
    elif g[0:6] == "ALPSRP":
        exp = pr["PALSAR"]
    else:
        exp = pr["Legacy"]

    regex = re.compile(exp)
    return regex.match(g)

def find_granules_list(i, granules, level):
    g = dict()
    t = dict()
    n = 0

    pr = {
           "Sentinel-1": r'S1[ABCD]_\w{2}_\w{4}_\w{4}_\d{8}T\d{6}_\d{8}T\d{6}_\d{6}_\w{6}_\w{4}',
           "PALSAR":     r'ALPSRP\d{9}',
           "Legacy":     r'[JER][12]_\d{5}_\w{3}_F\d+'
         }
    for plat in pr:
        log.debug("Looking for " + plat)
        regex = re.compile(pr[plat])
        for granule_name in regex.findall(granules):
            if granule_name not in g.values():
                n += 1
                k = zpad6(i) + '-' + zpad6(n)
                g[k] = granule_name
                log.debug('Found ' + granule_name)

                if plat in t:
                    t[plat] += 1
                else:
                    t[plat] = 1

    if n > 1:
        for p in t.keys():
            s = ""
            if t[p] > 1: s= "s"
            log.info("Found %d %s granule%s" % (t[p], p, s))

    return g


def find_granules_search(platforms, beammodes, starttime, endtime, wkt, point, max_results, level,
                         wget_options=None):
    s = "param?"
    if platforms is not None:
        if platforms == "Sentinel":
            platforms = "Sentinel-1A,Sentinel-1B"
        s += "platform=" + platforms + "&"
    if beammodes is not None:
        s += "beamMode=" + beammodes + "&"
    if starttime is not None:
        s += "start=" + starttime.strftime("%Y-%m-%dT%H:%M:%SUTC") + "&"
    if endtime is not None:
        s += "end=" + endtime.strftime("%Y-%m-%dT%H:%M:%SUTC") + "&"
    if wkt is not None:
        s += "intersectsWith=" + wkt + "&"
    elif point is not None:
        s += "intersectsWith=POINT(" + point.replace(","," ") + ")&"

    if max_results > 0:
        s += ("maxResults={0}&".format(max_results * 6))
    s += "output=CSV"

    return do_granule_search(s, level, max_results, wget_options=wget_options)


def do_granule_search(search_str, level, max_results, wget_options=None):
    if 'granule_list' in search_str:
        i = search_str.find('granule_list')+13
        g = search_str[i:search_str.find('&',i)]
        log.info('Searching for ' + g)

    cmd = ('wget -O- %s "https://api.daac.asf.alaska.edu/services/search/' + search_str + '"') % wget_options
    output, ok = execute(cmd, raise_on_error=True)

    granules = dict()
    for line in output.split("\n"):
        l = line.strip()
        if 'SAR' in l and ',' in l:
            fields = list(csv.reader([l]))[0]
            log.debug(str(fields))
            if len(fields)>8:
                g = fields[0].strip() # granule name
                if not valid_granule(g):
                    log.debug("Ignoring bogus: " + g)
                    continue
                t = fields[8].strip() # time
                p = guess_platform(g)
                if len(g) > 0:
                    log.debug('Inspecting: ' + g)
                    if p is not None:
                        log.debug('===> Level: ' + str(level))
                        if str_for_plat_lvl(guess_platform(g), fudge_level(g, level)) in l:
                            log.debug("Adding {0}: {1}".format(t,g))
                            granules[t] = g
                            if max_results > 0 and len(granules) >= max_results:
                                log.debug("Reached maximum granules, stopping")
                                break
                        else:
                            log.debug("Not adding: {0} ({1}, {2}, {3}".format(g, guess_platform(g), fudge_level(g, level), str_for_plat_lvl(guess_platform(g), fudge_level(g, level))))
                    else:
                        log.info('Could not guess platform for {0}, skipping'.format(g))

    if len(granules.keys()) == 0:
        log.warning('No results')
 
    return granules


def get_url(granule, level, wget_options=None):
    cmd = ('wget -O- %s "https://api.daac.asf.alaska.edu/services/search/param?granule_list=%s&output=CSV"' % (wget_options, granule))
    output, ok = execute(cmd)
    if not ok:
        return None

    url = None

    for line in output.split("\n"):
        l = line.strip()
        if granule in l and str_for_plat_lvl(guess_platform(granule), fudge_level(granule, level)) in l:
            if level == "BROWSE":
                m = re.search('(http.*jpg)', l)
            else:
                m = re.search('(http.*zip)', l)
            if m is not None:
                url = m.group(0)

    if url is None:
        # Could be because this product is DELETED and a new version is available.  The search will return that
        # so we just need to loosen our search through the results
        for line in output.split("\n"):
            l = line.strip()
            if str_for_plat_lvl(guess_platform(granule), fudge_level(granule, level)) in l:
                if level == "BROWSE":
                    m = re.search('(http.*jpg)', l)
                else:
                    m = re.search('(http.*zip)', l)
                if m is not None:
                    url = m.group(0)

    log.debug("URL: " + str(url))
    return url


def verify_download(cfg, tmpName, finalName):
    try:
        if 'S1A' in tmpName or 'S1B' in tmpName:
            log.debug('Verifying Sentinel granule ' + tmpName)
            uzDir = os.path.join(cfg.tmpDir, "tmp_" + str(os.getpid()))
            log.debug('Unzipping into ' + uzDir)
            d = do_unzip(tmpName, uzDir)
            ok = verify_checksums(d)
            shutil.rmtree(uzDir)
        elif 'ALPSRP' in tmpName:
            log.debug('Verifying PALSAR granule ' + tmpName)
            ok = verify_zip(tmpName)
        else:
            ok = True
    except Exception as e:
        log.info('Verify failed: ' + str(e))
        ok = False

    if ok:
        log.info('Verification passed for ' + os.path.basename(tmpName))
        log.debug('Moving: {0} -> {1}'.format(tmpName, cfg.dataDir))
        os.rename(tmpName, finalName)

    return ok


def try_kludge_url(granule, lvl):
    if granule[0:2] == 'S1':
        # S1B_IW_GRDH_1SSV_20170325T154634_20170325T154648_004867_008801_B35E
        # 0123456789012345678901234567890123456789012345678901234567890123456
        # 0         1         2
        if granule[7:10] == 'GRD':
            url = 'https://datapool.asf.alaska.edu/{0}_{1}{2}/S{3}/{4}.zip'.format(
                granule[7:10], granule[10], granule[14], granule[2], granule)
        else:
            url = 'https://datapool.asf.alaska.edu/{0}/S{1}/{2}.zip'.format(
                granule[7:10], granule[2], granule)
        log.info('URL not found, guessing: ' + url)
        return url
    elif granule[0:2] == 'E1' or granule[0:2] == 'E2' or granule[0:2] == 'R1' or granule[0:2] == 'J1':
        url = 'https://datapool.asf.alaska.edu/L0/{0}/{1}.zip'.format(granule[0:2], granule.replace('STD','STD_L0'))
        return url
    return None

def list_downloads(cfg):
    for k in cfg.new:
        log.info("To download: " + cfg.new[k])

def download(cfg, keys_queue):
    if cfg.dry_run or cfg.debug:
        list_downloads(cfg)
        if cfg.dry_run:
            return

    program_start_time = cfg.program_start_time
    while True:
        nfails = 0
        try:
            k = keys_queue.get(block=False)
        except queue.Empty:
            break
        granule = cfg.new[k]

        url = None #get_url(granule, cfg.level)
        if url is None:
            url = try_kludge_url(granule, cfg.level)
        if url is None:
            log.warning("No URL found for: " + granule)
            continue

        path, fileName = os.path.split(url)
        realName = os.path.join(cfg.tmpDir, fileName)
        dataStr = realName + ".tmp"
        completeName = os.path.join(cfg.dataDir, fileName)

        resume_opt = ""
        get_it = True

        if granule in already_fetched:
            log.info('In already fetched list: ' + granule)
            continue
        if os.path.isfile(completeName):
            log.info('Already have: ' + granule)
            continue

        log.info("Downloading " + granule + ": " + url)

        if os.path.isfile(realName):
            if cfg.overwrite:
                log.warning('Already exists: ' + realName + ' (overwriting)')
                os.remove(realName)
            elif cfg.ignore:
                log.info('Already exists: ' + realName + ' (skipped)')
                get_it = False
                if os.path.isfile(dataStr):
                    os.remove(dataStr)
            else:  # cfg.resume
                if os.path.isfile(dataStr):
                    # Just ignore the real file, try to resume the .tmp
                    pass
                else:
                    log.info('Already exists: ' + realName + ' (skipped)')
                    get_it = False

        if os.path.isfile(dataStr):
            if cfg.ignore:
                log.info('Already exists: ' + dataStr + ' (skipped)')
                get_it = False
            elif cfg.overwrite:
                log.warning('Already exists: ' + dataStr + ' (overwriting)')
                os.remove(dataStr)
            else:  ## cfg.resume, now the default
                log.info('Already exists: ' + dataStr + ' (resuming)')
                resume_opt = "--continue"

        if get_it:
            cmd = ("wget %s %s --http-user='%s' --http-password='%s' -O %s %s" % (cfg.wget_options, resume_opt, cfg.user, cfg.password, dataStr, url))

            start_time = time.time()
            o,ok = execute(cmd, dataStr, quiet=True)
            if not ok:
                log.info('Failed to download: ' + granule)
                nfails += 1
                continue

            elapsed_time = time.time() - start_time
            rate = 0

            if 'The file is already fully retrieved; nothing to do' in o:
                log.info("Already completely downloaded: %s" % granule) # TODO Add counter
            else:
                log.info("Completed: %s" % granule) # TODO Add counter
                add_to_fetched(cfg.already_fetched_file, granule)
 
                # 162432397 (155M) remaining
                amt = None
                total = 0

                if resume_opt == "--continue":
                    m = re.search('(\d+) \(*?\) remaining', o)
                    if m is not None:
                        amt = int(m.group(1))
                        log.debug("Remaining: "+str(amt))

                m = re.search('saved \[(\d+)', o)
                if m is not None:
                    total = int(m.group(1))
                    if amt is None:
                        amt = total

                if amt is None:
                    amt_str = "(none) " 
                elif amt>1024*1024*1024:
                    amt_str = "(%.2f GB) " % (amt/1024.0/1024.0/1024.0)
                elif amt>1024*1024:
                    amt_str = "(%.2f MB) " % (amt/1024.0/1024.0)
                elif amt>1024:
                    amt_str = "(%.2f KB) " % (amt/1024.0)
                else:
                    amt_str = ""

                rate = amt/float(elapsed_time)/1024.0/1024.0

                log.debug('Downloaded %d/%d bytes %sin %ds (%.2f MB/s)' % (amt, total, amt_str, elapsed_time, rate))

                seconds_downloading = 0
                total_mb_downloaded = 0
                seconds_downloading += elapsed_time
                total_elapsed_time = time.time() - program_start_time
                total_mb_downloaded += amt/1024.0/1024.0
                eff = seconds_downloading*100.0/float(total_elapsed_time)
                orate = total_mb_downloaded/float(total_elapsed_time)
                orate2 = total_mb_downloaded/float(seconds_downloading)

                log.debug('Elapsed time: %ds, downloading %ds (%.2f%% efficiency).  Overall rate: %.2f MB/s (%.2f while transferring)'
                           % (total_elapsed_time, seconds_downloading, eff, orate, orate2))
                log.info("Rate: {0:.2f} MB/s, Size: {1:.2f} MB".format(orate2, total_mb_downloaded))

            log.debug('Renaming: {0} -> {1}'.format(dataStr, realName))
            os.rename(dataStr, realName)

            if not cfg.debug:
                log.debug('Downloaded %s in %ds (%.2f MB/s)' % (fileName, elapsed_time, rate))

            if cfg.get_orb and guess_platform(fileName) == "Sentinel":
                get_orb(fileName)

            if cfg.delay > 0:
                log.info("Waiting " + str(cfg.delay) + "s")
                time.sleep(cfg.delay)

        if os.path.isfile(realName):
            if cfg.verify:
                ok = verify_download(cfg, realName, completeName)
                if ok:
                    del cfg.new[k]
                else:
                    nfails += 1
                    os.unlink(realName)
            else:
                log.debug('Moving: {0} -> {1}'.format(fileName, cfg.dataDir))
                os.rename(realName, completeName)
                del cfg.new[k]

        elif os.path.isfile(completeName):
            log.debug("Skipped already completed: " + fileName)
        else:
            log.warning("As far as I know this should never happen.")

def download_granules(cfg, trynum=0):
    if cfg.new is None or len(cfg.new.keys()) == 0:
        log.error("No granules to get!")
        return

    # Check data directory
    if len(cfg.dataDir) >0 and not os.path.exists(cfg.dataDir):
        raise FileNotFoundError(f'Data directory {cfg.dataDir} does not exist')

    n = len(cfg.new.keys())
    log.info("Have %d granules to get" % n)

    nfails = 0

    # Get the data
    cfg.dataDir = os.path.abspath(cfg.dataDir)
    keys = sorted(cfg.new.keys())
    keys_queue = queue.Queue()
    for k in keys:
        keys_queue.put(k)
    threads = [threading.Thread(target=download, args=(cfg, keys_queue))
            for _ in range(cfg.threads_num)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    if nfails > 0:
        if trynum < cfg.max_retries:
            log.info('Retrying failed granules')
            download_granules(cfg, trynum=trynum+1)
        else:
            log.info('Reached maximum retries.')


def get_xml_attribute(obj, key, attr):
    """Search for and return a given XML attribute from the given XML tree structure"""

    o = obj.find(key)
    if o is not None and attr in o.attrib:
        return o.attrib[attr]
    else:
        raise Exception('Required XML attribute not found: ' + key + '["' + attr + '"]')


def get_text_attr(doc, attr):
    """
    Parses an XML attribute, returns it as a string.

    If there is no such attribute, returns the empty string.
    """

    a = doc.find(attr)
    if a is None:
        return ''
    else:
        return a.text


def find_manifest(dir_):
    """
    Look in the specified directory for "manifest.safe"

    If the file can't be found, returns None.
    """
    # Look for manifest.safe
    p = os.path.join(dir_, 'manifest.safe')
    if os.path.isfile(p):
        return p

    raise Exception('manifest.safe file was not found in ' + dir_)


def verify_checksums(dir_):
    """For every MD5 given in the manifest.safe file, check the associated file's MD5 to make sure it matches"""

    safe_file = find_manifest(dir_)
    log.debug('Verifying MD5 checksums in manifest file')

    doc = etree.parse(safe_file)
    if doc is None:
        raise Exception('Could not parse manifest.safe file')
    dos = doc.find('dataObjectSection')
    if dos is None:
        raise Exception('No dataObjectSection found in manifest.xml! Could not verify MD5 sums')
    for obj in dos.findall('dataObject'):
        loc = get_xml_attribute(obj, 'byteStream/fileLocation', 'href')
        if loc.startswith('./'):
            loc = loc[2:]

        md5 = get_text_attr(obj, 'byteStream/checksum')
        log.debug('Found: ' + loc + ', ' + md5)

        path = os.path.join(os.path.dirname(safe_file), loc)
        log.debug('Path: ' + path)
        if not os.path.isfile(path):
            raise Exception('manifest.safe has checksum for file that was not found: ' + loc)

        sz = os.stat(path).st_size
        file_size = get_xml_attribute(obj, 'byteStream', 'size')
        if file_size is not None and sz == int(file_size):
            log.debug('File Size ok: ' + str(file_size) + ' bytes')
        else:
            raise Exception('File size check failed for ' + os.path.basename(path) + '.  Manifest: ' + str(file_size) + ', actual: ' + str(sz))

        md5_2 = get_md5sum(path)
        if md5 == md5_2:
            log.debug('MD5 ok: ' + md5)
        else:
            raise Exception('Checksum failed for ' + os.path.basename(path) + '. Manifest: ' + md5 + ', actual: ' + md5_2)

    log.debug('All MD5 checks passed.')
    return True


def get_md5sum(filename):
    """Returns MD5 string of the given file"""

    hasher = hashlib.md5()
    with open(filename, 'rb') as afile:
        buf = afile.read()
        hasher.update(buf)
    return hasher.hexdigest()


def verify_zip(zipFilePath):
    log.debug('Verifying ' + zipFilePath)

    if not os.path.isfile(zipFilePath):
        raise Exception('File not found: ' + zipFilePath)

    z = zipfile.ZipFile(zipFilePath)
    ret = z.testzip()

    if ret is not None:
        raise Exception("First bad file in zip: " + ret)
    else:
        return True


def do_unzip(zipFilePath, destDir):
    """
    Unzips the path+file zipFilePath into the specified destDir
    """

    log.debug('Unzipping ' + zipFilePath + ' into ' + destDir)

    if not os.path.isfile(zipFilePath):
        raise Exception('File not found: ' + zipFilePath)

    try:
        z = zipfile.ZipFile(zipFilePath)

        z.extractall(destDir)

        retdir = None
        for name in z.namelist():
            (dirName, fileName) = os.path.split(name)
            if fileName == '':
                # directory
                newDir = destDir + '/' + dirName
                if not os.path.exists(newDir):
                    raise Exception('Directory not extracted! => ' + newDir)
                if retdir is None:
                    retdir = newDir
                    break

        z.close()
    except Exception as e:
        log.info(zipFilePath + ': Bad zip file!')
        tb = traceback.format_exc().split("\n")
        for tbline in tb:
            line = tbline.rstrip()
            if len(line) > 0:
                log.info(line)

        log.info('Trying command-line unzip')
        try:
            execute('unzip -d ' + destDir + ' ' + zipFilePath, raise_on_error=True)

            # Here we use our insider knowledge
            retdir = os.path.join(destDir, os.path.basename(zipFilePath).replace('.zip', '') + '.SAFE')

        except Exception:
            log.info(zipFilePath + ': Bad zip file again!')
            raise e

    return retdir


def main():
    (cfg, args) = get_cla()
    cfg = get_config(cfg)

    setup_logger(cfg.debug)

    if cfg.version:
        log.info("Version: " + _hyp3lib_version)
        sys.exit(0)

    cfg.program_start_time = time.time()
    log.debug("Start Time: " + str(datetime.datetime.fromtimestamp(cfg.program_start_time)))
    log.debug("Version: " + _hyp3lib_version)

    n_args = len(args)
    log.debug("Args: " + str(args))
  
    if cfg.wget_options is None:
        cfg.wget_options = ""

    log.debug("cfg.l1 = " + str(cfg.l1))

    cfg.level = None
    if cfg.l0:
        cfg.level = "L0"
    if cfg.slc:
        cfg.level = "SLC"
    if cfg.l1:
        cfg.level = "L1"
    if cfg.browse:
        cfg.level = "BROWSE"
    if cfg.rtc:
        cfg.level = "RTC"
 
    if cfg.dataDir is None:
        cfg.dataDir = ""

    if not cfg.tmpDir:
        cfg.tmpDir = os.path.join(cfg.dataDir, "download")

    if not os.path.isdir(cfg.tmpDir):
        log.info("Creating download directory: " + cfg.tmpDir)
        os.mkdir(cfg.tmpDir)

    if n_args == 0 and \
        cfg.platforms is None and \
        cfg.beammodes is None and \
        cfg.start_time is None and \
        cfg.end_time is None and \
        cfg.point is None and \
        cfg.wkt is None:
        log.critical("Please specify granules to get, or search criteria.")
        sys.exit(-1)

    if n_args > 0 and (
            cfg.platforms is not None or
            cfg.beammodes is not None or
            cfg.start_time is not None or
            cfg.end_time is not None or
            cfg.point is not None or
            cfg.wkt is not None
    ):
        log.warning("Your search criteria will be ignored since you specified granules manually")

    if cfg.wkt is not None and cfg.point is not None:
        log.critical("You can't specify both a WKT string and a point")
        sys.exit(-1)

    if cfg.user is None or cfg.password is None:
        log.critical("Please provide your URS login credentials")
        sys.exit(-1)

    if cfg.delayStr:
        cfg.delay = int(cfg.delayStr)
    else:
        cfg.delay = 0

    if cfg.maxStr:
        cfg.max = int(cfg.maxStr)
    else:
        cfg.max = -1

    if cfg.already_fetched_file:
        get_already_fetched(cfg.already_fetched_file)

    # install signal handling for SIGTERM, SIGQUIT, and SIGHUP
    def signal_handler(signum, frame):
        # this ugly line creates a lookup table between signal numbers and their "nice" names
        signum_to_names = dict((getattr(signal, n), n) for n in dir(signal) if n.startswith('SIG') and '_' not in n )
        log.critical("Received a {0}; bailing out.".format(signum_to_names[signum]))
        sys.exit(1)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGQUIT, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)

    log.debug("Debug messages: " + str(cfg.debug))

    log.debug("Download Dir: " + cfg.tmpDir)
    log.debug("Data Dir: " + cfg.dataDir)
    log.debug("Delay: " + str(cfg.delay) + "s")
    log.debug("Max Results: " + str(cfg.max))
    log.debug("Max Retries: " + str(cfg.max_retries))
    log.debug("Get Orbits: " + str(cfg.get_orb))

    if n_args > 0:
        cfg.new = dict()
        for i in range(0,n_args):
            g1 = find_granules_file(i, args[i], cfg)
            cfg.new.update(g1)
        download_granules(cfg)

    else:
        start = None
        if cfg.start_time:
            if "T" in cfg.start_time:
                start = datetime.datetime.strptime(cfg.start_time, "%Y-%m-%dT%H:%M:%S")
            else:
                start = datetime.datetime.strptime(cfg.start_time, "%Y-%m-%d")
            log.debug("Start Time: " + str(start))

        end = None
        if cfg.end_time:
            if "T" in cfg.end_time:
                end = datetime.datetime.strptime(cfg.end_time, "%Y-%m-%dT%H:%M:%S")
            else:
                end = datetime.datetime.strptime(cfg.end_time, "%Y-%m-%d")
            log.debug("End Time: " + str(start))

        log.debug("Platform(s): " + str(cfg.platforms))
        log.debug("Beam Mode(s): " + str(cfg.beammodes))
        log.debug("WKT: " + str(cfg.wkt))
        log.debug("Point: " + str(cfg.point))
        log.debug("Level: " + str(cfg.level))
        log.debug("Dry Run: " + str(cfg.dry_run))

        cfg.new = find_granules_search(cfg.platforms, cfg.beammodes, start, end, cfg.wkt, cfg.point, cfg.max,
                                       cfg.level, wget_options=cfg.wget_options)

        #g = find_granules('ALOS', 'FBS', datetime.datetime.strptime("2008-12-01T00:00:00", "%Y-%m-%dT%H:%M:%S"),
        #                  datetime.datetime.strptime("2008-12-31T00:00:00", "%Y-%m-%dT%H:%M:%S"),
        #                  "-155.08,65.82,-153.28,64.47,-149.94,64.55,-149.50,63.07,-153.5,61.91")
        download_granules(cfg)

        log.info("Done")


if __name__ == '__main__':
    main()
