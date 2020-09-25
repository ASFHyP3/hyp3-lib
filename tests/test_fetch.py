import os

import pytest
import requests
import responses

from hyp3lib import fetch


def test_write_credentials_to_netrc_file(tmp_path):
    os.environ['HOME'] = str(tmp_path)
    output_file = tmp_path / '.netrc'

    fetch.write_credentials_to_netrc_file('foo', 'bar')
    assert output_file.is_file()
    with open(output_file, 'r') as f:
        assert f.read() == 'machine urs.earthdata.nasa.gov login foo password bar\n'

    fetch.write_credentials_to_netrc_file('already_there', 'this call should do nothing')
    with open(output_file, 'r') as f:
        assert f.read() == 'machine urs.earthdata.nasa.gov login foo password bar\n'

    fetch.write_credentials_to_netrc_file('append', 'this', domain='domain', append=True)
    with open(output_file, 'r') as f:
        assert f.read() == 'machine urs.earthdata.nasa.gov login foo password bar\n' \
                           'machine domain login append password this\n'


@responses.activate
def test_download_file(safe_data, tmp_path):
    with open(os.path.join(safe_data, 'granule_name.txt')) as f:
        text = f.read()

    responses.add(
        responses.GET, 'http://hyp3.asf.alaska.edu/foobar.txt', body=text,
        status=200,
    )

    download_path = fetch.download_file('http://hyp3.asf.alaska.edu/foobar.txt', directory=tmp_path)

    assert download_path == os.path.join(tmp_path, 'foobar.txt')
    assert os.path.exists(download_path)
    with open(download_path) as f:
        assert f.read() == text


@responses.activate
def test_download_file_in_chunks(safe_data, tmp_path):
    with open(os.path.join(safe_data, 'granule_name.txt')) as f:
        text = f.read()

    responses.add(
        responses.GET, 'http://hyp3.asf.alaska.edu/foobar.txt', body=text,
        status=200,
    )

    download_path = fetch.download_file('http://hyp3.asf.alaska.edu/foobar.txt', directory=tmp_path, chunk_size=1)

    assert download_path == os.path.join(tmp_path, 'foobar.txt')
    assert os.path.exists(download_path)
    with open(download_path) as f:
        assert f.read() == text


def test_download_file_none():
    with pytest.raises(requests.exceptions.InvalidURL):
        _ = fetch.download_file(url=None)
