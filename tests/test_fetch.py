import os
from pathlib import Path

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


def test_get_download_path():
    url = 'https://somewebsite.com/foo.bar'
    content_disposition_quoted = 'attachment; filename="filename.jpg"'
    content_disposition_unquoted = 'attachment; filename=filename.jpg'
    content_disposition_no_filename = 'attachment;'
    content_disposition_empty = 'attachment; filename=""'
    dir_as_str = 'dir'
    dir_as_path = Path(dir_as_str)

    result = fetch._get_download_path(url, content_disposition_quoted)
    assert result == Path('filename.jpg')

    result = fetch._get_download_path(url, content_disposition_unquoted)
    assert result == Path('filename.jpg')

    result = fetch._get_download_path(url, content_disposition_no_filename)
    assert result == Path('foo.bar')

    result = fetch._get_download_path(url, content_disposition_empty)
    assert result == Path('foo.bar')

    result = fetch._get_download_path(url)
    assert result == Path('foo.bar')

    result = fetch._get_download_path(url, directory=dir_as_str)
    assert result == Path('dir/foo.bar')

    result = fetch._get_download_path(url, directory=dir_as_path)
    assert result == Path('dir/foo.bar')

    result = fetch._get_download_path(url, content_disposition_unquoted, dir_as_str)
    assert result == Path('dir/filename.jpg')

    with pytest.raises(ValueError):
        fetch._get_download_path('https://foo.com')


@responses.activate
def test_download_file(safe_data, tmp_path):
    with open(os.path.join(safe_data, 'granule_name.txt')) as f:
        text = f.read()

    responses.add(responses.GET, 'http://hyp3.asf.alaska.edu/foobar.txt', body=text)

    download_path = fetch.download_file('http://hyp3.asf.alaska.edu/foobar.txt', directory=tmp_path)

    assert download_path == os.path.join(tmp_path, 'foobar.txt')
    assert os.path.exists(download_path)
    with open(download_path) as f:
        assert f.read() == text


@responses.activate
def test_download_file_content_disposition(tmp_path):
    responses.add(
        responses.GET, 'http://hyp3.asf.alaska.edu/foobar.txt',
        headers={'content-disposition': 'attachment; filename="filename.jpg"'}
    )

    download_path = fetch.download_file('http://hyp3.asf.alaska.edu/foobar.txt', directory=tmp_path)

    assert download_path == os.path.join(tmp_path, 'filename.jpg')
    assert os.path.exists(download_path)


@responses.activate
def test_download_file_in_chunks(safe_data, tmp_path):
    with open(os.path.join(safe_data, 'granule_name.txt')) as f:
        text = f.read()

    responses.add(responses.GET, 'http://hyp3.asf.alaska.edu/foobar.txt', body=text)

    download_path = fetch.download_file('http://hyp3.asf.alaska.edu/foobar.txt', directory=tmp_path, chunk_size=1)

    assert download_path == os.path.join(tmp_path, 'foobar.txt')
    assert os.path.exists(download_path)
    with open(download_path) as f:
        assert f.read() == text


@responses.activate
def test_download_file_auth(tmp_path):
    def request_callback(request):
        assert request.headers['Authorization'] == 'Basic Zm9vOmJhcg=='
        return 200, {}, 'body'

    responses.add_callback(responses.GET, 'http://hyp3.asf.alaska.edu/foobar.txt', callback=request_callback)

    fetch.download_file('http://hyp3.asf.alaska.edu/foobar.txt', directory=tmp_path, auth=('foo', 'bar'))
    assert (tmp_path / 'foobar.txt').exists()


def test_download_file_none():
    with pytest.raises(requests.exceptions.MissingSchema):
        _ = fetch.download_file(url=None)
