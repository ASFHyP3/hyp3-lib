"""Utilities for fetching things from external endpoints"""

import logging
import os
import requests


# TODO:? Max retries, verify, timeout
def download_file(url, directory=None, headers=None, chunk_size=None):
    logging.info(f'Downloading {url}')
    # TODO: works?
    local_filename = os.path.join(directory, url.split("/")[-1])
    with requests.get(url, headers=headers, stream=True) as r:
        if r.status_code == 401:
            logging.error("Invalid username or password")
        r.raise_for_status()
        with open(local_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
    return local_filename
