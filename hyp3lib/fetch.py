"""Utilities for fetching things from external endpoints"""

import logging
import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def download_file(url: str, directory: str = '', chunk_size=None, retries=2, backoff_factor=1):
    """Download a file

    Args:
        url: URL of the file to download
        directory: Directory location to place files into
        chunk_size: Size to chunk the download into
        retries: Number of retry's to attempt
        backoff_factor: Factor for calculating time between retries

    Returns:
        download_path: The path to the downloaded file
    """
    logging.info(f'Downloading {url}')

    try:
        download_path = os.path.join(directory, url.split("/")[-1])
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
    return download_path
