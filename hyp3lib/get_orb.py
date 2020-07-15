"""Get Sentinel-1 orbit file(s) from ASF or ESA website"""

import argparse
import logging
import os
import re
import sys
from datetime import datetime, timedelta

import requests
from lxml import html
from requests.adapters import HTTPAdapter
from six.moves.urllib.parse import urlparse

from hyp3lib import OrbitDownloadError
from hyp3lib.fetch import download_file
from hyp3lib.verify_opod import verify_opod


def _get_asf_orbit_url(search_url, platform, timestamp, verify=True):
    if not search_url.endswith('/'):
        search_url += '/'

    hostname = urlparse(search_url).hostname
    session = requests.Session()
    session.mount(hostname, HTTPAdapter(max_retries=10))
    page = session.get(search_url, timeout=60, verify=verify)
    tree = html.fromstring(page.content)
    file_list = []
    for item in tree.xpath('//a[@href]//@href'):
        if 'EOF' in item:
            file_list.append(item)

    d1 = 0
    best = None
    for item in file_list:
        if 'S1' in item:
            item = item.replace(' ', '')
            item1 = item
            this_plat = item[0:3]
            item = item.replace('T', '')
            item = item.replace('V', '')
            t = re.split('_', item)
            if len(t) > 7:
                start = t[6]
                end = t[7].replace('.EOF', '')
                if start < timestamp < end and platform == this_plat:
                    d = ((int(timestamp) - int(start)) + (int(end) - int(timestamp))) / 2
                    if d > d1:
                        best = item1.replace(' ', '')
                        d1 = d
    return search_url + best


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

    if provider == 'ESA':
        delta = timedelta(seconds=60)
        start_time = datetime.strptime(time_stamps[0], '%Y%m%dT%H%M%S') - delta
        end_time = datetime.strptime(time_stamps[1], '%Y%m%dT%H%M%S') + delta

        params = {
            "product_type": orbit_type.upper(),
            "product_name__startswith": platform,
            "validity_start__lt": start_time.strftime('%Y-%m-%dT%H:%M:%S'),
            "validity_stop__gt": end_time.strftime('%Y-%m-%dT%H:%M:%S'),
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
        url = f'https://s1qc.asf.alaska.edu/{orbit_type.lower()}/'
        granule = os.path.basename(granule).rstrip('/')

        platform = granule[0:3]

        orbit_url = _get_asf_orbit_url(url, platform, time_stamps[0].replace('T', ''))
        return orbit_url

    else:
        raise OrbitDownloadError(f'Unkown orbit file provider {provider}')


def download_sentinel_orbit_file(granule: str, directory: str = None, providers=('ESA', 'ASF')):
    """Download a Sentinel-1 Orbit file

    Args:
        granule: Granule name to find an orbit file for
        directory: Directory to save the orbit files into
        providers: Iterable of providers to attempt to download the orbit file from, in order of preference

    Returns: Tuple of:
        orbit_file: The downloaded orbit file
        provider: The provider used to download the orbit file from

    """
    for provider in providers:
        orbit_url = get_orbit_url(granule, 'AUX_POEORB', provider=provider)
        if not orbit_url:
            orbit_url = get_orbit_url(granule, 'AUX_RESORB', provider=provider)

        if not orbit_url:
            break

        orbit_file = download_file(
            orbit_url, directory=directory, headers={'User-Agent': 'python3 asfdaac/apt-insar'}, chunk_size=5242880
        )

        try:
            verify_opod(orbit_file)
        except ValueError:
            raise OrbitDownloadError(f'Downloaded orbit file is invalid: {orbit_file}')

        return orbit_file, provider

    raise OrbitDownloadError(f'Unable to find a matching orbit file from providers: {providers}')


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument('safe_files', help='Sentinel-1 SAFE file name(s)', nargs="*")
    parser.add_argument('-p', '--provider', choices=['ASF', 'ESA'], help='Name of orbit file provider organization')
    parser.add_argument('-d', '--directory', help='Download files to this directory')
    args = parser.parse_args()

    if args.provider is None:
        args.provider = ('ASF', 'ESA')

    out = logging.StreamHandler(stream=sys.stdout)
    out.addFilter(lambda record: record.levelno <= logging.INFO)
    err = logging.StreamHandler()
    err.setLevel(logging.WARNING)
    logging.basicConfig(format='%(message)s', level=logging.INFO, handlers=(out, err))

    for safe in args.safe_files:
        try:
            orbit_file, provided_by = download_sentinel_orbit_file(
                safe, directory=args.directory, providers=tuple(args.provider)
            )
            logging.info("Downloaded orbit file {} from {}".format(orbit_file, provided_by))
        except OrbitDownloadError as e:
            logging.warning(f'WARNING: unable to download orbit file for {safe}\n    {e}')


if __name__ == "__main__":
    main()
