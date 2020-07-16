import os
from datetime import datetime

import pytest
import requests
import responses

from hyp3lib import fetch


@responses.activate
def test_download_file(safe_data):
    with open(os.path.join(safe_data, 'granule_name.txt')) as f:
        text = f.read()

    responses.add(
        responses.GET, 'http://hyp3.asf.alaska.edu/foobar.txt', body=text,
        status=200,
    )

    download_path = fetch.download_file('http://hyp3.asf.alaska.edu/foobar.txt')

    assert download_path == 'foobar.txt'
    assert os.path.exists(download_path)
    with open(download_path) as f:
        assert f.read() == text


@responses.activate
def test_download_file_in_chunks(safe_data):
    with open(os.path.join(safe_data, 'granule_name.txt')) as f:
        text = f.read()

    responses.add(
        responses.GET, 'http://hyp3.asf.alaska.edu/foobar.txt', body=text,
        status=200,
    )

    download_path = fetch.download_file('http://hyp3.asf.alaska.edu/foobar.txt', chunk_size=1)

    assert download_path == 'foobar.txt'
    assert os.path.exists(download_path)
    with open(download_path) as f:
        assert f.read() == text


def test_download_file_retries():
    backoff_factor = 1
    total_retries = 2
    expected_time = backoff_factor * (2 ** (total_retries - 1))

    before = datetime.now()
    with pytest.raises(requests.exceptions.RetryError):
        _ = fetch.download_file('http://httpstat.us/500', backoff_factor=backoff_factor, retries=total_retries)
    after = datetime.now()
    assert (after - before).seconds >= expected_time


def test_download_file_none():
    with pytest.raises(requests.exceptions.InvalidURL):
        _ = fetch.download_file(url=None)
