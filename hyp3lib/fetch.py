"""Utilities for fetching things from external endpoints"""

import logging
import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def download_file(url, directory=None, headers=None, chunk_size=None, retries=3, backoff_factor=10):
    logging.info(f'Downloading {url}')

    local_filename = os.path.join(directory, url.split("/")[-1])

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
        with open(local_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
    return local_filename
