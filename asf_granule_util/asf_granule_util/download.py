import requests
import json
import tqdm
import math
import os
import zipfile as zf
import contextlib

from .exceptions import InvalidGranuleException


def download(
        granule,
        credentials,
        directory=os.getcwd(),
        progess_bar=False,
        unzip=True
):
    granule_str = str(granule)
    zip_url = get_download_url(granule_str)
    download_redirect = requests.get(zip_url)

    username, password = [credentials[k] for k in ['username', 'password']]
    dl_request = requests.get(
        download_redirect.url,
        auth=(username, password),
        stream=True
    )

    total_size = int(dl_request.headers.get('content-length', 0))
    download = get_download(
        dl_request,
        progess_bar,
        total_size
    )

    granule_path = get_granule_path(directory, granule_str)
    do_download(download, granule_path, total_size)

    if unzip:
        do_unzip(granule_path)


def get_download(download, progess_bar, total_size):
    block_size = 1024

    if progess_bar:
        download = get_progress_download(download, total_size, block_size)
    else:
        download = get_raw_download(download, block_size)

    return download


def get_progress_download(download, total_size, block_size):
    return tqdm.tqdm(
        download.iter_content(block_size),
        total=math.ceil(total_size//block_size),
        unit='B',
        unit_scale=True
    )


def get_raw_download(download, block_size):
    return download.iter_content(block_size)


def get_granule_path(directory, granule_str):
    granule_zip = granule_str + '.zip'

    return os.path.join(directory, granule_zip)


def do_download(download, directory, total_size):
    with open(directory, 'wb') as f:
        wrote = stream_to_file(f, download)

    if total_size != 0 and wrote != total_size:
        raise InvalidGranuleException("ERROR downloading granule")


def stream_to_file(f, download):
    wrote = 0
    for chunk in download:
        wrote += len(chunk)
        f.write(chunk)

    return wrote


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


def do_unzip(self, path):
    output_path = os.path.dirname(path)

    with zipfile(path) as zf:
        zf.extractall(output_path)


@contextlib.contextmanager
def zipfile(path):
    zip_ref = zf.ZipFile(path, 'r')
    yield zip_ref
    zip_ref.close()
