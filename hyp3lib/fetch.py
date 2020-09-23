"""Utilities for fetching things from external endpoints"""

import logging
from pathlib import Path
from typing import Union

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


def download_file(url: str, directory: Union[Path, str] = '.', chunk_size=None, retries=2, backoff_factor=1) -> str:
    """Download a file

    Args:
        url: URL of the file to download
        directory: Directory location to place files into
        chunk_size: Size to chunk the download into
        retries: Number of retries to attempt
        backoff_factor: Factor for calculating time between retries

    Returns:
        download_path: The path to the downloaded file
    """
    logging.info(f'Downloading {url}')

    try:
        download_path = Path(directory) / url.split("/")[-1]
    except AttributeError:
        raise requests.exceptions.InvalidURL(f'Invalid URL provided: {url}')

    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 503, 504],
    )

    session.mount('https://', HTTPAdapter(max_retries=retry_strategy))
    session.mount('http://', HTTPAdapter(max_retries=retry_strategy))

    with session.get(url, stream=True) as s:
        s.raise_for_status()
        with open(download_path, "wb") as f:
            for chunk in s.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
    session.close()

    return str(download_path)
