"""Get Sentinel-1 orbit file(s) from ASF or ESA website"""

import argparse
import logging
import os
import re
import sys
from datetime import datetime

import requests
from lxml import html
from requests.adapters import HTTPAdapter
from six.moves.urllib.parse import urlparse
from urllib3.util.retry import Retry

from hyp3lib import OrbitDownloadError
from hyp3lib.fetch import download_file
from hyp3lib.verify_opod import verify_opod


def _get_asf_orbit_url(orbit_type, platform, timestamp):
    search_url = f'https://s1qc.asf.alaska.edu/{orbit_type.lower()}/'

    hostname = urlparse(search_url).hostname
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=10,
        status_forcelist=[429, 500, 503, 504],
    )
    session.mount(hostname, HTTPAdapter(max_retries=retries))
    response = session.get(search_url)
    response.raise_for_status()
    tree = html.fromstring(response.content)
    file_list = [file for file in tree.xpath('//a[@href]//@href')
                 if file.startswith(platform) and file.endswith('.EOF')]

    d1 = 0
    best = None
    for file in file_list:
        file = file.strip()
        t = re.split('_', file.replace('T', '').replace('V', ''))
        if len(t) > 7:
            start = t[6]
            end = t[7].replace('.EOF', '')
            if start < timestamp < end:
                d = ((int(timestamp) - int(start)) + (int(end) - int(timestamp))) / 2
                if d > d1:
                    best = file
                    d1 = d

    if best is not None:
        return search_url + best

    return None


def get_orbit_url(granule: str, orbit_type: str = 'AUX_POEORB', provider: str = 'ESA'):
    """Get the URL of an orbit file from a provider

    Args:
        granule: Granule name to find an orbit file for
        orbit_type: Orbit type to download
        provider: Povider name to download the orbit file from

    Returns:
        orbit_url: The url to the matched orbit file
    """
    platform = granule[0:3]
    time_stamps = re.split('_+', granule)[4:6]

    if provider.upper() == 'ESA':
        params = {
            "product_type": orbit_type.upper(),
            "product_name__startswith": platform,
            "validity_start__lt": datetime.strptime(time_stamps[0], '%Y%m%dT%H%M%S').strftime('%Y-%m-%dT%H:%M:%S'),
            "validity_stop__gt": datetime.strptime(time_stamps[1], '%Y%m%dT%H%M%S').strftime('%Y-%m-%dT%H:%M:%S'),
            "ordering": "-creation_date",
            "page_size": "1",
        }

        response = requests.get(url='https://qc.sentinel1.eo.esa.int/api/v1/', params=params)
        response.raise_for_status()
        qc_data = response.json()

        orbit_url = None
        if qc_data["results"]:
            orbit_url = qc_data["results"][0]["remote_url"]
        return orbit_url

    elif provider.upper() == 'ASF':
        orbit_url = _get_asf_orbit_url(orbit_type.lower(), platform, time_stamps[0].replace('T', ''))
        return orbit_url

    raise OrbitDownloadError(f'Unknown orbit file provider {provider}')


def _download_and_verify_orbit(url: str, directory: str = ''):
    orbit_file = download_file(url, directory=directory)
    try:
        verify_opod(orbit_file)
    except ValueError:
        raise OrbitDownloadError(f'Downloaded an invalid orbit file {orbit_file}')

    return orbit_file


def downloadSentinelOrbitFile(
        granule: str, directory: str = '', providers=('ESA', 'ASF'), orbit_types=('AUX_POEORB', 'AUX_RESORB')
):
    """Download a Sentinel-1 Orbit file

    Args:
        granule: Granule name to find an orbit file for
        directory: Directory to save the orbit files into
        providers: Iterable of providers to attempt to download the orbit file from, in order of preference
        orbit_types: Iterable of orbit file types to attempt to download, in order of preference

    Returns: Tuple of:
        orbit_file: The downloaded orbit file
        provider: The provider used to download the orbit file from

    """
    for orbit_type in orbit_types:
        for provider in providers:
            try:
                url = get_orbit_url(granule, orbit_type, provider=provider)
                orbit_file = _download_and_verify_orbit(url, directory=directory)
                if orbit_file:
                    return orbit_file, provider
            except (requests.RequestException, OrbitDownloadError):
                logging.warning(
                    f'Error encountered fetching {orbit_type} orbit file from {provider}; looking for another',
                )
                continue

    raise OrbitDownloadError(f'Unable to find a valid orbit file from providers: {providers}')


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('safe_files', help='Sentinel-1 SAFE file name(s)', nargs="*")
    parser.add_argument('-p', '--provider', nargs='*', default=['ESA', 'ASF'],  choices=['ESA', 'ASF'],
                        help="Name(s) of the orbit file providers' organization, in order of preference")
    parser.add_argument('-t', '--orbit-types', nargs='*', default=['AUX_POEORB', 'AUX_RESORB'],
                        choices=['MPL_ORBPRE', 'AUX_POEORB', 'AUX_PREORB', 'AUX_RESORB', 'AUX_RESATT'],
                        help="Name(s) of the orbit file providers' organization, in order of preference. "
                             "See https://qc.sentinel1.eo.esa.int/")
    parser.add_argument('-d', '--directory', default=os.getcwd(), help='Download files to this directory')
    args = parser.parse_args()

    out = logging.StreamHandler(stream=sys.stdout)
    out.addFilter(lambda record: record.levelno <= logging.INFO)
    err = logging.StreamHandler()
    err.setLevel(logging.WARNING)
    logging.basicConfig(format='%(message)s', level=logging.INFO, handlers=(out, err))

    for safe in args.safe_files:
        try:
            orbit_file, provided_by = downloadSentinelOrbitFile(
                safe, directory=args.directory, providers=args.provider, orbit_types=args.orbit_types
            )
            logging.info("Downloaded orbit file {} from {}".format(orbit_file, provided_by))
        except OrbitDownloadError as e:
            logging.warning(f'WARNING: unable to download orbit file for {safe}\n    {e}')


if __name__ == "__main__":
    main()
