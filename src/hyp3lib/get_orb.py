"""Get Sentinel-1 orbit file(s) from ASF or ESA website"""

import argparse
import logging
import os
import re
import sys
from datetime import datetime
from typing import Optional, Tuple
from urllib.parse import urlparse

import requests
from lxml import html
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from hyp3lib import OrbitDownloadError
from hyp3lib.fetch import download_file

ESA_CREATE_TOKEN_URL = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token'
ESA_DELETE_TOKEN_URL = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/account/sessions'


class EsaToken:
    """Context manager for authentication tokens for the ESA Copernicus Data Space Ecosystem (CDSE)"""

    def __init__(self, username: str, password: str):
        """
        Args:
            username: CDSE username
            password: CDSE password
        """
        self.username = username
        self.password = password
        self.token = None
        self.session_id = None

    def __enter__(self) -> str:
        data = {
            'client_id': 'cdse-public',
            'grant_type': 'password',
            'username': self.username,
            'password': self.password,
        }
        response = requests.post(ESA_CREATE_TOKEN_URL, data=data)
        response.raise_for_status()
        self.session_id = response.json()['session_state']
        self.token = response.json()['access_token']
        return self.token

    def __exit__(self, exc_type, exc_val, exc_tb):
        response = requests.delete(
            url=f'{ESA_DELETE_TOKEN_URL}/{self.session_id}',
            headers={'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'},
        )
        response.raise_for_status()


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
    file_list = [
        file for file in tree.xpath('//a[@href]//@href') if file.startswith(platform) and file.endswith('.EOF')
    ]

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


def _get_esa_orbit_url(orbit_type: str, platform: str, start_time: datetime, end_time: datetime):
    search_url = 'https://catalogue.dataspace.copernicus.eu/odata/v1/Products'

    date_format = '%Y-%m-%dT%H:%M:%SZ'
    params = {
        '$filter': f"Collection/Name eq 'SENTINEL-1' and "
        f"startswith(Name, '{platform}_OPER_{orbit_type}_OPOD_') and "
        f'ContentDate/Start lt {start_time.strftime(date_format)} and '
        f'ContentDate/End gt {end_time.strftime(date_format)}',
        '$orderby': 'Name desc',
        '$top': 1,
    }

    response = requests.get(search_url, params=params)
    response.raise_for_status()
    data = response.json()

    orbit_url = None
    if data['value']:
        product_id = data['value'][0]['Id']
        orbit_url = f'https://zipper.dataspace.copernicus.eu/download/{product_id}'

    return orbit_url


def get_orbit_url(granule: str, orbit_type: str = 'AUX_POEORB', provider: str = 'ESA'):
    """Get the URL of a Sentinel-1 orbit file from a provider

    Args:
        granule: Sentinel-1 granule name to find an orbit file for
        orbit_type: Orbit type to download
        provider: Provider name to download the orbit file from

    Returns:
        orbit_url: The url to the matched orbit file
    """
    platform = granule[0:3]
    start_time, end_time = re.split('_+', granule)[4:6]

    if provider.upper() == 'ESA':
        start_time = datetime.strptime(start_time, '%Y%m%dT%H%M%S')
        end_time = datetime.strptime(end_time, '%Y%m%dT%H%M%S')
        return _get_esa_orbit_url(orbit_type, platform, start_time, end_time)

    elif provider.upper() == 'ASF':
        orbit_url = _get_asf_orbit_url(orbit_type.lower(), platform, start_time.replace('T', ''))
        return orbit_url

    raise OrbitDownloadError(f'Unknown orbit file provider {provider}')


def downloadSentinelOrbitFile(
    granule: str,
    directory: str = '',
    providers=('ESA', 'ASF'),
    orbit_types=('AUX_POEORB', 'AUX_RESORB'),
    esa_credentials: Optional[Tuple[str, str]] = None,
):
    """Download a Sentinel-1 Orbit file

    Args:
        granule: Granule name to find an orbit file for
        directory: Directory to save the orbit files into
        providers: Iterable of providers to attempt to download the orbit file from, in order of preference
        orbit_types: Iterable of orbit file types to attempt to download, in order of preference
        esa_credentials: Copernicus Data Space Ecosystem (CDSE) username and password

    Returns: Tuple of:
        orbit_file: The downloaded orbit file
        provider: The provider used to download the orbit file from

    """
    if 'ESA' in providers and esa_credentials is None:
        raise ValueError('esa_credentials must be provided if ESA in providers')
    for orbit_type in orbit_types:
        for provider in providers:
            try:
                url = get_orbit_url(granule, orbit_type, provider=provider)
                if provider == 'ESA':
                    with EsaToken(*esa_credentials) as token:
                        orbit_file = download_file(url, directory=directory, token=token)
                else:
                    orbit_file = download_file(url, directory=directory)
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
    parser.add_argument('safe_files', help='Sentinel-1 SAFE file name(s)', nargs='*')
    parser.add_argument(
        '-p',
        '--provider',
        nargs='*',
        default=['ESA', 'ASF'],
        choices=['ESA', 'ASF'],
        help="Name(s) of the orbit file providers' organization, in order of preference",
    )
    parser.add_argument(
        '-t',
        '--orbit-types',
        nargs='*',
        default=['AUX_POEORB', 'AUX_RESORB'],
        choices=['MPL_ORBPRE', 'AUX_POEORB', 'AUX_PREORB', 'AUX_RESORB', 'AUX_RESATT'],
        help="Name(s) of the orbit file providers' organization, in order of preference. "
        'See https://qc.sentinel1.eo.esa.int/',
    )
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
            logging.info('Downloaded orbit file {} from {}'.format(orbit_file, provided_by))
        except OrbitDownloadError as e:
            logging.warning(f'WARNING: unable to download orbit file for {safe}\n    {e}')


if __name__ == '__main__':
    main()
