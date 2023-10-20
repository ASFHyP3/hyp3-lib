import os
from unittest.mock import patch

import responses

from hyp3lib import get_orb

_GRANULE = 'S1A_IW_SLC__1SSV_20150621T120220_20150621T120232_006471_008934_72D8'


@responses.activate
def test_download_sentinel_orbit_file_esa(tmp_path):
    responses.add(responses.GET, 'https://foo.bar/hello.txt', body='content')

    with patch('hyp3lib.get_orb.get_orbit_url', return_value='https://foo.bar/hello.txt'):
        responses.add(responses.GET, 'https://foo.bar/hello.txt', body='content')
        orbit_file, provider = get_orb.downloadSentinelOrbitFile(_GRANULE, providers=('ESA',), directory=str(tmp_path))

    assert provider == 'ESA'
    assert os.path.exists(orbit_file)
    assert orbit_file == str(tmp_path / 'hello.txt')


@responses.activate
def test_get_orbit_url_esa_poeorb():
    search_url = ('https://catalogue.dataspace.copernicus.eu/odata/v1/Products?'
                  '%24filter=Collection%2FName+eq+%27SENTINEL-1%27+and+'
                  'startswith%28Name%2C+%27S1A_OPER_AUX_POEORB_OPOD_%27%29+and+ContentDate%2FStart+lt+2015-06-21T12%3A02%3A20Z+and+ContentDate%2FEnd+gt+2015-06-21T12%3A02%3A32Z&%24orderby=ModificationDate+desc&%24top=1')
    search_response = {'value': [{'Id': 'myProductId'}]}
    responses.add(responses.GET, search_url, json=search_response)

    orbit_url = get_orb.get_orbit_url(_GRANULE, provider='ESA')
    assert orbit_url == "https://zipper.dataspace.copernicus.eu/download/myProductId"


@responses.activate
def test_get_orbit_url_esa_resorb():
    search_url = 'https://catalogue.dataspace.copernicus.eu/odata/v1/Products?%24filter=Collection%2FName+eq+%27SENTINEL-1%27+and+startswith%28Name%2C+%27S1A_OPER_AUX_RESORB_OPOD_%27%29+and+ContentDate%2FStart+lt+2015-06-21T12%3A02%3A20Z+and+ContentDate%2FEnd+gt+2015-06-21T12%3A02%3A32Z&%24orderby=ModificationDate+desc&%24top=1'
    search_response = {'value': [{'Id': 'myProductId'}]}
    responses.add(responses.GET, search_url, json=search_response)

    orbit_url = get_orb.get_orbit_url(_GRANULE, provider='ESA', orbit_type='AUX_RESORB')
    assert orbit_url == "https://zipper.dataspace.copernicus.eu/download/myProductId"


def test_get_orbit_url_asf():
    orbit_url = get_orb.get_orbit_url(_GRANULE, provider='ASF')

    assert 'https://s1qc.asf.alaska.edu/aux_poeorb/' \
           'S1A_OPER_AUX_POEORB_OPOD_20150711T121908_V20150620T225944_20150622T005944.EOF' \
           == orbit_url
