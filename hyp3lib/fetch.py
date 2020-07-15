"""Utilities for fetching things from external endpoints"""

import logging
import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def download_file(url: str, directory: str = '.', headers=None, chunk_size=None, retries=3, backoff_factor=10):
    """Download a file

    Args:
        url: URL of the file to download
        directory: Directory location to place files into
        headers: Dictionary of headers to add to the the download request
        chunk_size: Size to chunk the download into
        retries: Number of retry's to attempt
        backoff_factor: Factor for calculating time between retries

    Returns:
        download_path: The path to the downloaded file
    """
    logging.info(f'Downloading {url}')

    download_path = os.path.join(directory, url.split("/")[-1])

    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 503, 504],
    )

    session.mount('https://', HTTPAdapter(max_retries=retry))
    session.mount('http://', HTTPAdapter(max_retries=retry))

    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(download_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
    return download_path
