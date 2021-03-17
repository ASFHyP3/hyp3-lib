"""Utilities for fetching things from external endpoints"""
import cgi
import logging
from os.path import basename
from pathlib import Path
from typing import Optional, Tuple, Union
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

EARTHDATA_LOGIN_DOMAIN = 'urs.earthdata.nasa.gov'


def write_credentials_to_netrc_file(username: str, password: str,
                                    domain: str = EARTHDATA_LOGIN_DOMAIN, append: bool = False):
    """Write credentials to .netrc file"""
    netrc_file = Path.home() / '.netrc'
    if netrc_file.exists() and not append:
        logging.warning(f'Using existing .netrc file: {netrc_file}')
    else:
        with open(netrc_file, 'a') as f:
            f.write(f'machine {domain} login {username} password {password}\n')


def _get_download_path(url: str, content_disposition: str = None, directory: Union[Path, str] = '.'):
    filename = None
    if content_disposition is not None:
        _, params = cgi.parse_header(content_disposition)
        filename = params.get('filename')
    if not filename:
        filename = basename(urlparse(url).path)
    if not filename:
        raise ValueError(f'could not determine download path for: {url}')
    return Path(directory) / filename


def download_file(url: str, directory: Union[Path, str] = '.', chunk_size=None, retries=2, backoff_factor=1,
                  auth: Optional[Tuple[str, str]] = None) -> str:
    """Download a file

    Args:
        url: URL of the file to download
        directory: Directory location to place files into
        chunk_size: Size to chunk the download into
        retries: Number of retries to attempt
        backoff_factor: Factor for calculating time between retries
        auth: Username and password for HTTP Basic Auth

    Returns:
        download_path: The path to the downloaded file
    """
    logging.info(f'Downloading {url}')

    session = requests.Session()
    session.auth = auth

    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    session.mount('https://', HTTPAdapter(max_retries=retry_strategy))
    session.mount('http://', HTTPAdapter(max_retries=retry_strategy))

    with session.get(url, stream=True) as s:
        download_path = _get_download_path(s.url, s.headers.get('content-disposition'), directory)
        s.raise_for_status()
        with open(download_path, "wb") as f:
            for chunk in s.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
    session.close()

    return str(download_path)
