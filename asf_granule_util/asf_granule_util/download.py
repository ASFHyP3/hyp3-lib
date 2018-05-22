import requests
import json
import tqdm
import math
import os

from .exceptions import InvalidGranuleException


def download(granule, credentials, directory=os.getcwd(), progess_bar=False):
    granule_str = str(granule)
    zip_url = get_download_url(granule_str)
    download_redirect = requests.get(zip_url)

    username, password = [credentials[k] for k in ['username', 'password']]
    download = requests.get(
        download_redirect.url,
        auth=(username, password),
        stream=True
    )

    dl_iter = get_download_iter(
        progess_bar,
        download
    )

    granule_path = get_granule_path(directory, granule_str)
    do_download(dl_iter, granule_path)


def get_granule_path(directory, granule_str):
    granule_zip = granule_str + '.zip'

    return os.path.join(directory, granule_zip)


def get_download_iter(progess_bar, download):
    block_size = 1024

    if progess_bar:
        dl_iter = get_progress_iter(download, block_size)
    else:
        dl_iter = get_raw_iter(download, block_size)

    return dl_iter


def get_progress_iter(download, block_size):
    total_size = int(download.headers.get('content-length', 0))

    return tqdm.tqdm(
        download.iter_content(block_size),
        total=math.ceil(total_size//block_size),
        unit='B',
        unit_scale=True
    )


def get_raw_iter(download, block_size):
    return download.iter_content(block_size)


def do_download(download_iter, directory):
    with open(directory, 'wb') as f:
        wrote = 0
        for chunk in download_iter:
            wrote += len(chunk)
            f.write(chunk)

    if total_size != 0 and wrote != total_size:
        raise InvalidGranuleException("ERROR downloading granule")


def get_download_url(granule_str):
    api_url = 'https://api.daac.asf.alaska.edu/services/search/param'

    resp = requests.post(api_url, {
        'granule_list': granule_str,
        'output': 'JSON'
    })

    responses = json.loads(resp.text)[0]
    urls = [resp['downloadUrl'] for resp in responses]

    zip_urls = [url for url in urls if url.endswith('.zip')]

    return zip_urls.pop()
