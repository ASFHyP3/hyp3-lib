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
    search_url = 'https://scihub.copernicus.eu/gnss/api/stub/products' \
                 '?filter=%28platformname%3ASentinel-1+AND+producttype%3AAUX_POEORB+AND+filename%3AS1A%2A+' \
                 'AND+beginPosition%3A%5B%2A+TO+2015-06-21T12%3A02%3A20Z%5D+' \
                 'AND+endPosition%3A%5B2015-06-21T12%3A02%3A32Z+TO+NOW%5D%29' \
                 '&limit=1&offset=0&sortedby=ingestiondate&order=desc'
    search_response = {'products': [{'uuid': 'myUUID'}]}
    responses.add(responses.GET, search_url, json=search_response)

    orbit_url = get_orb.get_orbit_url(_GRANULE, provider='ESA')
    assert orbit_url == "https://scihub.copernicus.eu/gnss/odata/v1/Products('myUUID')/$value"


@responses.activate
def test_get_orbit_url_esa_resorb():
    search_url = 'https://scihub.copernicus.eu/gnss/api/stub/products' \
                 '?filter=%28platformname%3ASentinel-1+AND+producttype%3AAUX_RESORB+AND+filename%3AS1A%2A+' \
                 'AND+beginPosition%3A%5B%2A+TO+2015-06-21T12%3A02%3A20Z%5D+' \
                 'AND+endPosition%3A%5B2015-06-21T12%3A02%3A32Z+TO+NOW%5D%29' \
                 '&limit=1&offset=0&sortedby=ingestiondate&order=desc'
    search_response = {'products': [{'uuid': 'myUUID'}]}
    responses.add(responses.GET, search_url, json=search_response)

    orbit_url = get_orb.get_orbit_url(_GRANULE, provider='ESA', orbit_type='AUX_RESORB')
    assert orbit_url == "https://scihub.copernicus.eu/gnss/odata/v1/Products('myUUID')/$value"


def test_get_orbit_url_asf():
    orbit_url = get_orb.get_orbit_url(_GRANULE, provider='ASF')

    assert 'https://s1qc.asf.alaska.edu/aux_poeorb/' \
           'S1A_OPER_AUX_POEORB_OPOD_20150711T121908_V20150620T225944_20150622T005944.EOF' \
           == orbit_url
